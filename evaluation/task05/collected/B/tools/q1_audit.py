"""Extract/check local Q1 artifacts and record measured metadata; no product decisions."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def path(name):
    p = (ROOT / name).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError("Path outside assigned workspace")
    return p


def read(name):
    return path(name).read_text(encoding="utf-8")


def digest(name):
    return hashlib.sha256(path(name).read_bytes()).hexdigest()


def write_new_json(name, value):
    p = path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    json.loads(text)
    with p.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def section(name):
    content = read("context.md")
    body = content.split("## Предыдущая запись: " + name + "\n", 1)[1]
    return json.loads(body.split("\n## ", 1)[0].strip())


def check():
    context = read("context.md")
    registry = {
        match.group(1): ("materials/" + match.group(2), match.group(3))
        for match in re.finditer(r"^\| ([^|]+) \| ([^|]+) \| ([0-9a-f]{64}) \|$", context, re.MULTILINE)
    }
    checked_ids = ["OWNER-INSTRUCTION", "OUTPUT-v2-validation-plan", "S005v1-original", "S002v2-meta", "S002v2-original", "ECON-v2", "CORRECTION-v2", "CORRECTION-CHECK-v2"]
    source_checks = []
    for key in checked_ids:
        filename, expected = registry[key]
        actual = digest(filename)
        assert actual == expected, (key, "source digest mismatch")
        source_checks.append({"id": key, "path": filename, "sha256": actual, "registry_matches": True})
    now = datetime.fromisoformat("2026-12-19T12:00:00+03:00")
    commitments = section("commitments")
    deltas = {
        k["id"]: (now - datetime.fromisoformat(k["due_at"])).total_seconds() / 86400
        for k in commitments if k["due_at"] is not None
    }
    assert deltas == {"K-PROTOCOL": 32.0, "K-CAPABILITY": 32.0}
    conditions = section("conditions")
    fresh = next(c for c in conditions if c["id"] == "G-FRESHNESS")
    fresh_days = (now - datetime.fromisoformat(fresh["review_after"])).total_seconds() / 86400
    metrics = section("metrics")
    time = next(m for m in metrics if m["id"] == "M-TIME")
    planned_end_days = (now - datetime.fromisoformat(time["window"]["end"])).total_seconds() / 86400
    assert fresh_days == 18 and planned_end_days == 1
    assert all(m["window"] is None for m in metrics if m["id"] != "M-TIME")
    econ = json.loads(read("materials/evidence/calculations/economics-v2.json"))
    assert econ["source"] == {"id": "S002", "version": 2}
    assert econ["synthetic"] is True
    assert econ["base"]["support_minutes"] == "90.00"
    assert econ["base"]["margin_rub_per_account_month"] == "1500.0000"
    assert econ["base"]["surplus_before_unknown_costs_rub_month"] == "0.0000"
    protocols = []
    for branch in ("familiar", "variant"):
        name = f"notes/{branch}/q1-protocol.md"
        content = read(name)
        for term in ("K-PROTOCOL", "Обучение", "масштабирование", "Неизвестность", "не разрешены", "2026-12-19", "32"):
            assert term in content, (name, term)
        protocols.append({"branch": branch, "path": name, "sha256": digest(name), "content_read_and_checked": True})
    result = {
        "checked_at_utc": datetime.now().astimezone().isoformat(),
        "simulated_as_of": now.isoformat(),
        "context_sha256": digest("context.md"),
        "source_checks": source_checks,
        "new_inbox": {"path": "inbox/q1/repeated-correction-v1.txt", "sha256": digest("inbox/q1/repeated-correction-v1.txt"), "locator": "lines 1-3"},
        "date_calculations": {"formula": "(simulated_as_of - stored timestamp).total_seconds()/86400", "overdue_days_at_entry": deltas, "planned_M_TIME_end_days_ago": planned_end_days, "freshness_review_due_days_ago": fresh_days},
        "economic_result_reused": {"source": "S002@2", "artifact": "ECON-v2.base", "support_minutes": "90", "margin_rub_per_paid_account_month": "1500", "surplus_at_N20_before_unknown_costs_rub_month": "0", "new_import": False, "new_economic_recalculation": False},
        "protocols": protocols,
        "passed": True,
    }
    write_new_json("outputs/q1-verification.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def seal():
    verification = json.loads(read("outputs/q1-verification.json"))
    assert verification["passed"]
    for item in verification["protocols"]:
        assert digest(item["path"]) == item["sha256"]
    artifacts = ["responses/q1.md", "outputs/q1-verification.json", "tools/q1_audit.py"]
    for branch in ("familiar", "variant"):
        artifacts.extend([f"notes/{branch}/q1-protocol.md", f"notes/{branch}/q1-handoff.md"])
        note = read(f"notes/{branch}/q1-handoff.md")
        assert "completed_late" in note and "overdue" in note and "awaiting_decision" in note
    assert "Проектные правила Megafon присутствуют" in read("responses/q1.md")
    logs = []
    for filename in sorted(path("logs").glob("q1-*/result.json")):
        entry = json.loads(filename.read_text(encoding="utf-8"))
        assert Path(entry["cwd"]).resolve() == ROOT
        logs.append({"result": filename.relative_to(ROOT).as_posix(), **entry})
    ended = datetime.now().astimezone().isoformat()
    meta = {
        "task": "q1", "workspace": str(ROOT), "language": "ru", "project_rules_present": True,
        "started_utc": "2026-11-16T13:38:42+00:00", "ended_utc": ended,
        "time_scope": "Start is first observed clock reading after direct bootstrap; exact earlier bootstrap start is unavailable. End is local artifact sealing before final response delivery.",
        "simulated_as_of": "2026-12-19T12:00:00+03:00",
        "model": None, "model_settings": "unchanged; exact settings unknown", "tokens": None, "charges": None, "human_time": None,
        "external_help": {"subagents_spawned": 0, "live_web": False, "external_services": [], "parent_agent": "Assignment and isolation/runtime instructions; one outgoing progress update. No substantive answer supplied by parent."},
        "outside_capture": [
            {"kind": "bootstrap_read", "paths": ["request-q1.txt", "RUNTIME.md"], "tool": "exec_command/Get-Content", "details": "Only first direct shell command, permitted bootstrap. It omitted -Encoding UTF8 and displayed mojibake; repeated with UTF8 through capture."},
            {"kind": "time_read", "tool": "clock.curr_time", "value_utc": "2026-11-16T13:38:42+00:00"},
            {"kind": "write", "tool": "apply_patch", "paths": ["notes/familiar/q1-protocol.md", "notes/variant/q1-protocol.md", "tools/q1_audit.py", "notes/familiar/q1-handoff.md", "notes/variant/q1-handoff.md", "responses/q1.md"], "details": "New artifacts only; source files and former answers untouched."}
        ],
        "errors_and_repeats": [
            {"kind": "encoding", "resolved": True, "details": "Bootstrap output mojibake; UTF8 retry q1-bootstrap-utf8."},
            {"kind": "tool_output_truncation", "resolved": True, "details": "Large initial context output truncated in tool response; capture preserves exact full stdout. Relevant commitments/conditions/events read separately in q1-saved-followup, other necessary data from primary files."},
            {"kind": "unavailable_local_repository_utilities", "resolved": "task-specific workflow", "details": "Own workspace has no knowledge/procedures/decision-followup.md, knowledge/record-contracts.md or scripts/project_state.py. No parent/sibling reads attempted. Loaded supplied normalized checkpoint and primary owner instruction; preserved separate textual branch handoffs, as explicitly permitted by request-q1.txt."}
        ],
        "captures_completed_before_seal": logs,
        "sealing_capture": "logs/q1-finalize/result.json (written by capture after this process exits)",
        "measured_resources": {"completed_capture_count_before_seal": len(logs), "completed_capture_elapsed_seconds_sum_before_seal": sum(e["elapsed_seconds"] for e in logs), "scope": "Measured child command duration; excludes LLM deliberation, bootstrap, apply_patch and final in-flight capture. Full final duration remains in sealing_capture."},
        "artifacts": [{"path": name, "sha256": digest(name)} for name in artifacts],
        "state_scope": "Local scenario follow-up only. Prior context/materials unchanged. Real business decision awaiting_decision; no new strategic choice or external action.",
    }
    write_new_json("responses/q1-meta.json", meta)
    assert json.loads(read("responses/q1-meta.json"))["artifacts"] == meta["artifacts"]
    print(json.dumps({"response": "responses/q1.md", "meta": "responses/q1-meta.json", "ended_utc": ended, "artifact_count": len(artifacts), "verified": True}, ensure_ascii=False))


if __name__ == "__main__":
    {"check": check, "seal": seal}[sys.argv[1]]()
