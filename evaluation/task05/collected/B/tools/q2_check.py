"""Checks local Q2 artifacts and immutable prior records; no product decisions."""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def local(name):
    value = (ROOT / name).resolve()
    if not value.is_relative_to(ROOT):
        raise ValueError("Outside assigned workspace")
    return value


def read(name):
    return local(name).read_text(encoding="utf-8")


def sha(name):
    return hashlib.sha256(local(name).read_bytes()).hexdigest()


def save(name, data):
    out = local(name)
    out.parent.mkdir(parents=True, exist_ok=True)
    serial = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    json.loads(serial)
    with out.open("x", encoding="utf-8", newline="\n") as f:
        f.write(serial)


def prior_integrity():
    old = json.loads(read("responses/q1-meta.json"))
    results = []
    for artifact in old["artifacts_verified_before_metadata"]:
        assert sha(artifact["path"]) == artifact["sha256"], artifact["path"]
        results.append({**artifact, "unchanged": True})
    return results


def check():
    previous = prior_integrity()
    registry = {
        m.group(1): ("materials/" + m.group(2), m.group(3))
        for m in re.finditer(r"^\| ([^|]+) \| ([^|]+) \| ([0-9a-f]{64}) \|$", read("context.md"), re.MULTILINE)
    }
    ids = ["S001v1-original", "S001v1-extract", "OWNER-INSTRUCTION", "OUTPUT-v2-product-strategy", "OUTPUT-v2-communication-strategy", "OUTPUT-v2-validation-plan", "OUTPUT-v2-situation", "OUTPUT-v2-options"]
    source_checks = []
    for key in ids:
        name, expected = registry[key]
        assert sha(name) == expected, key
        source_checks.append({"id": key, "path": name, "sha256": expected, "matches_registry": True})
    incoming = {
        "familiar": "a329b857648cd3310ddb1e7ded9f3134707cc37122c186125f1c7afbab472168",
        "variant": "71284b4e378307a7414ea918b4eb7dd7dadc18b0b5f0c4fed50f971d8e6ccd43",
    }
    branches = []
    for branch, expected in incoming.items():
        source = f"inbox/q2/{branch}-withdrawal-v1.txt"
        assert sha(source) == expected
        amendment = f"outputs/{branch}/q2-amendment-v1.md"
        assert read(amendment).strip()
        branches.append({"branch": branch, "source": source, "source_sha256": expected, "source_locator": "lines 1-4; target S001@1 physical-page:1/block:5", "amendment": amendment, "amendment_sha256": sha(amendment)})
    result = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "simulated_as_of": "2026-12-19T13:00:00+03:00", "prior_artifacts": previous, "source_checks": source_checks, "branch_artifacts": branches, "passed": True}
    save("outputs/q2-verification.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def finalize():
    prior_integrity()
    checked = json.loads(read("outputs/q2-verification.json"))
    assert checked["passed"]
    for branch in checked["branch_artifacts"]:
        assert sha(branch["amendment"]) == branch["amendment_sha256"]
    artifacts = ["responses/q2.md", "outputs/q2-verification.json", "tools/q2_check.py"]
    for branch in ("familiar", "variant"):
        artifacts.extend([f"outputs/{branch}/q2-amendment-v1.md", f"notes/{branch}/q2-handoff.md"])
    for name in artifacts:
        assert read(name).strip(), name
    logs = []
    for file in sorted(local("logs").glob("q2-*/result.json")):
        content = json.loads(file.read_text(encoding="utf-8"))
        assert Path(content["cwd"]).resolve() == ROOT
        logs.append({"path": file.relative_to(ROOT).as_posix(), **content})
    end = datetime.now(timezone.utc).isoformat()
    meta = {
        "task": "q2", "workspace": str(ROOT), "project_rules_present": True,
        "started_utc": "2026-11-16T13:50:45Z", "ended_utc": end,
        "time_scope": "First observed clock reading through final artifact verification and metadata creation; final message delivery is later. Exact final command duration is in q2-finalize capture.",
        "simulated_as_of": "2026-12-19T13:00:00+03:00", "model": None, "model_settings": "Unchanged; exact model/settings unknown", "tokens": None, "charges": None, "human_time": None,
        "external_help": {"subagents_spawned": 0, "live_web": False, "external_services": [], "parent_agent": "Assigned Q2 and isolation instructions only. Outgoing progress message contained this agent's own analysis; no substantive reply or help received in Q2."},
        "outside_capture": [
            {"kind": "clock_read", "tool": "clock.curr_time", "value_utc": "2026-11-16T13:50:45Z"},
            {"kind": "new_file_writes", "tool": "apply_patch Add File", "paths": ["outputs/familiar/q2-amendment-v1.md", "outputs/variant/q2-amendment-v1.md", "tools/q2_check.py", "notes/familiar/q2-handoff.md", "notes/variant/q2-handoff.md", "responses/q2.md"]},
            {"kind": "shell_parse_failure_before_capture", "attempted_label": "q2-plan-locators-and-new-hashes", "details": "Nested PowerShell -Command regex used backslash-double-quote escaping. Parent PowerShell parser failed before capture.py started; no source reads/writes occurred. Tool exit_code=1; ParserError / ExpressionsMustBeFirstInPipeline. Displayed error was mojibake; exact subprocess stdout/stderr files do not exist because capture never began. The tool event retains the diagnostic."}
        ],
        "errors_and_repeats": [
            {"kind": "shell_quoting", "resolved": True, "details": "One pre-capture parser failure. Replaced the compound command with two independent captured commands: direct rg with a single-quoted regex in q2-plan-locators, and hash reading in q2-new-hashes. No repeated identical failed call."}
        ],
        "captures_completed_before_finalization": logs,
        "finalization_capture": "logs/q2-finalize/result.json",
        "measured_resources": {"completed_capture_count_before_finalization": len(logs), "completed_capture_elapsed_seconds_sum_before_finalization": sum(item["elapsed_seconds"] for item in logs), "scope": "Measured completed child processes only; excludes the in-flight finalization call, pre-capture parse failure, model deliberation and apply_patch. No token, charge or human-effort estimate."},
        "artifacts": [{"path": name, "sha256": sha(name)} for name in artifacts],
        "history_preserved": "All seven Q1 artifacts listed in q1-meta were hash-checked unchanged twice. Existing materials and context unchanged. No new economic calculations/imports or business decisions. Q2 current text uses per-branch amendments and handoffs, preserving OWNER-01 as historical simulated_accepted and real awaiting_decision.",
        "procedure_availability": "Unchanged from Q1: repo knowledge procedures/state utility are not in assigned workspace. No outside directory access; plain-text branch continuation as allowed by request.",
    }
    save("responses/q2-meta.json", meta)
    assert json.loads(read("responses/q2-meta.json"))["artifacts"] == meta["artifacts"]
    print(json.dumps({"verified": True, "response": "responses/q2.md", "meta": "responses/q2-meta.json", "ended_utc": end, "prior_q1_artifacts_unchanged": True}, ensure_ascii=False))


{"check": check, "finalize": finalize}[sys.argv[1]]()
