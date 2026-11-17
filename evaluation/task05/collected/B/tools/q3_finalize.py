"""Check unchanged history and save measured Q3 metadata, without product analysis."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def local(name):
    out = (ROOT / name).resolve()
    if not out.is_relative_to(ROOT):
        raise ValueError("Outside assigned workspace")
    return out


def sha(name):
    return hashlib.sha256(local(name).read_bytes()).hexdigest()


prior = []
for metadata, key in (("responses/q1-meta.json", "artifacts_verified_before_metadata"), ("responses/q2-meta.json", "artifacts")):
    saved = json.loads(local(metadata).read_text(encoding="utf-8"))
    for item in saved[key]:
        assert sha(item["path"]) == item["sha256"], item["path"]
        prior.append({**item, "unchanged": True})
inputs = []
for filename, locator in (("inbox/q3/repeated-correction-v2.txt", "lines 1-2"), ("inbox/q3/irrelevant-note-v1.txt", "lines 1-3")):
    inputs.append({"path": filename, "sha256": sha(filename), "locator": locator})
artifacts = ["responses/q3.md", "notes/familiar/q3-handoff.md", "notes/variant/q3-handoff.md", "tools/q3_finalize.py"]
for filename in artifacts:
    assert local(filename).read_text(encoding="utf-8").strip()
logs = []
for filename in sorted(local("logs").glob("q3-*/result.json")):
    item = json.loads(filename.read_text(encoding="utf-8"))
    assert Path(item["cwd"]).resolve() == ROOT
    logs.append({"path": filename.relative_to(ROOT).as_posix(), **item})
end = datetime.now(timezone.utc).isoformat()
meta = {
    "task": "q3", "workspace": str(ROOT), "project_rules_present": True,
    "started_utc": "2026-11-16T14:07:19Z", "ended_utc": end,
    "time_scope": "First observed clock through artifact verification and metadata write, before final message. Final capture records its own exact end/elapsed.",
    "simulated_as_of": "2026-12-19T14:00:00+03:00",
    "model": None, "model_settings": "Unchanged; exact settings/model unknown", "tokens": None, "charges": None, "human_time": None,
    "external_help": {"subagents_spawned": 0, "live_web": False, "external_services": [], "parent_agent": "Q3 task assignment and isolation instructions only; no substantive assistance received."},
    "outside_capture": [
        {"kind": "clock_read", "tool": "clock.curr_time", "value_utc": "2026-11-16T14:07:19Z"},
        {"kind": "new_file_writes", "tool": "apply_patch Add File", "paths": artifacts}
    ],
    "errors_and_repeats": [],
    "captures_completed_before_finalization": logs,
    "finalization_capture": "logs/q3-finalize/result.json",
    "measured_resources": {"completed_capture_count_before_finalization": len(logs), "completed_capture_elapsed_seconds_sum_before_finalization": sum(item["elapsed_seconds"] for item in logs), "scope": "Completed child processes only; excludes in-flight finalization, model deliberation and apply_patch. No estimated tokens, charges or human effort."},
    "new_inputs": inputs,
    "prior_artifacts_checked": prior,
    "new_artifacts": [{"path": filename, "sha256": sha(filename)} for filename in artifacts],
    "state_change": "Only minimal per-branch Q3 handoffs recording duplicate and decision-irrelevant inputs. No new product amendment, source version, calculation/import, commitment, review, choice or repeated decision request. Existing Q2 reviews and Q1 concerns remain open; historical OWNER-01 unchanged, real awaiting_decision.",
    "scope": "Own workspace only, no future-step or evaluator files. Prior responses, notes and materials not modified. No actual folder rename attempted."
}
target = local("responses/q3-meta.json")
with target.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(meta, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
assert json.loads(target.read_text(encoding="utf-8"))["new_artifacts"] == meta["new_artifacts"]
print(json.dumps({"verified": True, "response": "responses/q3.md", "meta": "responses/q3-meta.json", "unchanged_prior_artifact_count": len(prior), "new_inputs": inputs, "ended_utc": end}, ensure_ascii=False))
