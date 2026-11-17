"""Verify recorded comparison files and compute observations; does not score answers."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNS = {c: {"q1": f"q1-{c}-01", "q2": f"q2-{c}-02", "q3": f"q3-{c}-01"} for c in "AB"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def protocol(run):
    errors, failed_commands, requests, methods, sent_turns = [], [], [], {}, []
    for line_number, line in enumerate((run / "protocol.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        record = json.loads(line)
        message = record.get("message", {})
        method = message.get("method")
        if method:
            methods[method] = methods.get(method, 0) + 1
        locator = f"{run.name}/protocol.jsonl:{line_number}"
        if record["direction"] == "sent" and method == "turn/start":
            sent_turns.append({"at": record["at"], "locator": locator})
        if message.get("error"):
            errors.append({"at": record["at"], "locator": locator, "error": message["error"]})
        if record["direction"] == "received" and method and "id" in message:
            requests.append({"at": record["at"], "locator": locator, "method": method, "id": message["id"]})
        item = message.get("params", {}).get("item", {})
        if method == "item/completed" and item.get("type") == "commandExecution" and item.get("exitCode") not in (None, 0):
            failed_commands.append({"at": record["at"], "locator": locator, "command": item.get("command"),
                                    "exit_code": item.get("exitCode"), "status": item.get("status"),
                                    "output_excerpt": str(item.get("aggregatedOutput", ""))[:3000]})
    return {"methods": methods, "protocol_errors": errors, "failed_commands": failed_commands,
            "client_requests": requests, "sent_turns": sent_turns}


def main():
    target = HERE / "observations-final.json"
    if target.exists():
        raise SystemExit("Existing observations are preserved; choose a new explicit version for a rerun")
    output = {"observed_at": datetime.now(timezone.utc).isoformat(), "participants": {}, "checks": [],
              "limits": {"cost_money": None, "active_human_seconds": None,
                         "usage": "Final cumulative thread counters, not sum of per-phase cumulative snapshots",
                         "time": "Driver wall intervals include tools and model work; phases ran concurrently across participants"}}

    freeze = read(ROOT / "evaluation/task06/ordinary-freeze-manifest.json")
    mismatches = [rel for rel, expected in freeze["files"].items()
                  if sha(ROOT / "evaluation/task06/ordinary-current-v1" / rel) != expected]
    output["freeze"] = {"files_checked": len(freeze["files"]), "mismatches": mismatches}
    output["checks"].append({"name": "original_freeze_unchanged", "ok": not mismatches})

    settings_fields = ("model", "modelProvider", "reasoningEffort", "serviceTier", "approvalPolicy", "approvalsReviewer", "sandbox")
    for condition, phases in RUNS.items():
        participant = {"phases": {}, "wall_seconds_sum": 0}
        previous_tokens = 0
        for phase, dirname in phases.items():
            run = HERE / dirname
            result, operation, context, thread, exit_info = (read(run / name) for name in
                ("result.json", "operation.json", "context-check.json", "thread-result.json", "process-exit.json"))
            trace = protocol(run)
            snapshot = HERE / f"snapshot-{phase}-{condition}"
            snapshot_manifest = read(snapshot / "manifest.json")
            response = snapshot / f"{phase}.md"
            expected_request = ROOT / "evaluation/task06/ordinary-current-v1/prompts" / condition / f"{phase}.txt"
            observed_total = result.get("token_usage", {}).get("tokenUsage", {}).get("total")
            current_tokens = observed_total.get("totalTokens", 0) if observed_total else None
            phase_data = {
                "run": dirname, "result": result, "process_exit": exit_info,
                "settings": {key: thread.get(key) for key in settings_fields},
                "instruction_sources": thread.get("instructionSources"),
                "session_id": thread.get("thread", {}).get("sessionId"),
                "forked_from": thread.get("thread", {}).get("forkedFromId"),
                "context_check": context, "input_request_hash_matches_freeze": operation["input_hashes"][f"request-{phase}.txt"] == sha(expected_request),
                "response_snapshot_exists": response.exists(),
                "response_snapshot_sha256": sha(response) if response.exists() else None,
                "snapshot_files": len(snapshot_manifest["files"]),
                "trace": trace,
                "usage_increment_total_tokens": current_tokens - previous_tokens if current_tokens is not None else None,
            }
            if current_tokens is not None:
                output["checks"].append({"name": f"{condition}_{phase}_cumulative_tokens_monotonic", "ok": current_tokens >= previous_tokens})
                previous_tokens = current_tokens
            participant["phases"][phase] = phase_data
            participant["wall_seconds_sum"] += result["elapsed_seconds"]
            output["checks"].append({"name": f"{condition}_{phase}_completed_and_captured", "ok": result["outcome"] == "completed" and exit_info["code"] == 0 and response.exists() and len(trace["sent_turns"]) == 1})
            output["checks"].append({"name": f"{condition}_{phase}_known_context_checks", "ok": all(context[k] for k in ("sourceMatch", "settingsMatch", "freshMatch"))})
            output["checks"].append({"name": f"{condition}_{phase}_request_unchanged", "ok": phase_data["input_request_hash_matches_freeze"]})
            if phase == "q3":
                participant["final_cumulative_usage"] = observed_total
        output["participants"][condition] = participant

    for phase in ("q1", "q2", "q3"):
        a, b = (output["participants"][c]["phases"][phase] for c in "AB")
        output["checks"].append({"name": f"{phase}_settings_equal", "ok": a["settings"] == b["settings"]})
    first_start = min(stamp(output["participants"][c]["phases"]["q1"]["result"]["started_at"]) for c in "AB")
    last_end = max(stamp(output["participants"][c]["phases"]["q3"]["result"]["ended_at"]) for c in "AB")
    output["experiment_wall_window"] = {"started_at": first_start.isoformat(), "ended_at": last_end.isoformat(),
                                         "elapsed_seconds": (last_end - first_start).total_seconds(),
                                         "scope": "Includes waiting between participants, snapshots, driver diagnosis and phases; not a sum of overlapping intervals"}
    for previous, current in (("q1", "q2"), ("q2", "q3")):
        last_previous = max(stamp(output["participants"][c]["phases"][previous]["result"]["ended_at"]) for c in "AB")
        first_current = min(stamp(output["participants"][c]["phases"][current]["result"]["turn_started_at"]) for c in "AB")
        output["checks"].append({"name": f"{current}_after_both_{previous}", "ok": first_current > last_previous})
    failures = {}
    for condition in "AB":
        run = HERE / f"q2-{condition}-01"
        trace = protocol(run)
        failures[condition] = {"result": read(run / "result.json"), "actual_sandbox": read(run / "thread-result.json")["sandbox"],
                               "turns_sent": trace["sent_turns"], "context_check": read(run / "context-check.json")}
        output["checks"].append({"name": f"{condition}_failed_resume_sent_no_model_turn", "ok": not trace["sent_turns"]})
    output["preserved_driver_failures"] = failures
    output["all_structural_checks_pass"] = all(check["ok"] for check in output["checks"])
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(target), "checks": len(output["checks"]), "pass": output["all_structural_checks_pass"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
