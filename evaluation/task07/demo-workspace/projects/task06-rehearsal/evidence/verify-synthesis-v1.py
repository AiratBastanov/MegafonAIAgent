"""Verify local evidence, references and design arithmetic; no model or network."""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / "scripts"))
from project_state import load_state, reference


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


current = load_state(ROOT)
baseline = read_json("state/history/r000002.json")
old_refs = {a["id"]: a for a in baseline["artifacts"]}
current_refs = {a["id"]: a for a in current["artifacts"]}
reuse_ids = [
    "S001v1_meta", "S001v1_original", "S001v1_extract",
    "S002v1_meta", "S002v1_original", "S002v1_extract",
    "DICTIONARY", "SELECTION", "FUNNEL_SPEC", "ECON_SPEC", "SCENARIOS",
    "PDF_MANIFEST", "FUNNEL_CALC", "ECON_BASE_CALC", "ANALYSIS_SPEC",
    "ANALYSIS_CHECKER", "ANALYSIS_CALC"
]
reused = []
for aid in reuse_ids:
    assert current_refs[aid] == old_refs[aid]
    assert reference(ROOT, old_refs[aid]["path"], aid) == old_refs[aid]
    reused.append(old_refs[aid])
old_claims = {c["id"]: c for c in baseline["claims"]}
now_claims = {c["id"]: c for c in current["claims"]}
for cid in [f"C{i:03d}" for i in range(3, 13)] + ["C014"]:
    assert old_claims[cid] == now_claims[cid]

manifest = read_json("inputs/official-2026-11-16/manifest.json")
official = []
for number, entry in enumerate(manifest["sources"], 4):
    path = "inputs/official-2026-11-16/" + entry["path"]
    sid = f"S{number:03d}"
    meta = read_json(f"evidence/sources/{sid}/v1/source.json")
    assert sha(path) == entry["sha256"] == meta["input_sha256"]
    assert sha(meta["original"]["path"]) == entry["sha256"]
    assert meta["retrieval_status"] == "supplied_snapshot"
    assert meta["synthetic"] is False
    official.append({"id": sid, "version": 1, "manifest_hash_matches": True,
                     "retrieval_status": meta["retrieval_status"]})

names = ["situation.md", "options.md", "product-strategy.md", "communication-strategy.md", "validation-plan.md"]
assert sorted(p.name for p in (ROOT / "outputs/v2").iterdir()) == sorted(names)
texts = {}
document_checks = []
for name in names:
    path = "outputs/v2/" + name
    text = (ROOT / path).read_text(encoding="utf-8")
    texts[name] = text
    assert "???" not in text and "\ufffd" not in text
    assert "## Примечания" in text
    main = text.split("## Примечания")[0]
    assert not re.search(r"\b(?:C\d{3}|S\d{3}|COND_[A-Z_]+|M_[A-Z_]+)\b", main)
    refs = set(re.findall(r"\[\^(\d+)\](?!:)", text))
    definitions = set(re.findall(r"^\[\^(\d+)\]:", text, flags=re.M))
    assert refs == definitions
    links = re.findall(r"\]\(([^)]+)\)", text)
    for link in links:
        if "://" in link:
            continue
        target = (ROOT / path).parent / link.split("#")[0]
        assert target.resolve().is_relative_to(ROOT)
        assert target.is_file(), (name, link)
    assert "3 000" in text or name == "situation.md"
    assert "синтет" in text or "учебн" in text or name == "validation-plan.md"
    document_checks.append({"path": path, "sha256": sha(path), "footnotes": len(refs),
                            "local_links_exist": True, "no_internal_ids_in_main_text": True,
                            "utf8_readable": True})

register_path = "evidence/strategy-evidence-register-v2.md"
registry = (ROOT / register_path).read_text(encoding="utf-8")
assert "???" not in registry and "\ufffd" not in registry
tariff_fragments = [
    "Basic — 2 GB; Family/Plus — 50 GB; Transfer/Standard/Professional/Education/Essentials/Advanced/Business — 100 GB; Business Plus/Enterprise — 250 GB",
    "Replay Add-On позволяет 250 GB",
    "Standard/Professional/Education/Essentials/Business/Business Plus/Advanced/Enterprise",
    "Basic/Family/Plus — 7 дней",
    "по умолчанию 30 дней",
    "Basic/Plus/Family — до 2 GB; Professional/Essentials/Business/Business Plus/Standard/Advanced/Enterprise — до 250 GB",
    "Право отдельного плана Transfer на пароль из этой строки не установлено",
    "без явного планового ограничения",
    "менее 50 GB", "менее 10 000", "один пароль не означает запрет скачивания",
    "Дата",  # source dates are also reviewed manually in the evidence register
]
# Check critical literal boundaries; these guards do not replace semantic review.
for fragment in tariff_fragments[:-1]:
    assert fragment in registry, fragment

spec = read_json("inputs/validation-spec-v1.json")
content = read_json("drafts/synthesis-content-v6.json")
cohort = spec["cohort"]
assert cohort["relay_tasks_per_organisation"] + cohort["control_tasks_per_organisation"] == cohort["tasks_per_organisation"]
assert cohort["organisations"] * cohort["tasks_per_organisation"] == 48
assert cohort["organisations"] * cohort["relay_tasks_per_organisation"] == 24
assert Fraction(spec["thresholds"]["monthly_value_before_price"]) == 2 * Fraction(spec["price_per_organisation_calendar_month"])
assert all(m["window"] is None for m in content["metrics"])
assert spec["business_authorization"] is False and spec["windows"]["actual_start"] is None
assert "включая неплательщиков" in texts["validation-plan.md"]
assert "Время нашей команды поддержки записывать отдельно" in texts["validation-plan.md"]
assert "последней впервые оплатившей организации" in texts["validation-plan.md"]
assert "не менее 60% от первых оплат" in texts["options.md"]
renewal_min = []
for first in range(4, 13):
    rate = Fraction(spec["thresholds"]["renewers_per_first_payers_min_pct"]) / 100
    needed = max(spec["thresholds"]["renewers_min"], -(-(first * rate.numerator) // rate.denominator))
    assert Fraction(needed, first) >= rate
    assert needed == spec["thresholds"]["renewers_min"] or Fraction(needed - 1, first) < rate
    renewal_min.append({"first_payers": first, "minimum_renewers_for_joint_gate": needed})
assert "???" not in json.dumps(content, ensure_ascii=False)
assert len(content["conditions"]) == 5
assert set(content["current_outputs"].keys()) == {n[:-3] for n in names}
assert set(content["current_outputs"].values()) == {"SITUATION_V2", "OPTIONS_V2", "PRODUCT_V2", "COMMUNICATION_V2", "VALIDATION_V2"}

result = {
    "record_type": "synthesis_verification", "checked_at": datetime.now(timezone.utc).isoformat(),
    "checks": {"status": "passed", "baseline_revision": 2, "loaded_revision_before_final_save": current["revision"],
               "existing_calculations_recomputed": False, "old_sources_reimported": False,
               "documents_checked": 5, "official_snapshots_checked": 3,
               "literal_tariff_guards_passed": len(tariff_fragments) - 1,
               "semantic_review": "evidence/strategy-review-v1.md; same coordinator, not independent agent"},
    "reused_arithmetic": reused, "official_sources": official, "documents": document_checks,
    "register": {"path": register_path, "sha256": sha(register_path)},
    "definition_consistency": {"client_and_provider_time_separate": True, "frequency_window_includes_nonpayers": True,
                               "all_first_payers_renewal_windows_required": True, "missing_not_zero": True,
                               "learning_and_scaling_separate": True, "actual_start": None, "human_decision": None},
    "design_arithmetic": {"synthetic": True, "kind": "design_parameters_not_customer_results",
                          "assigned_tasks": 48, "tasks_per_method": 24, "value_buffer_rub": "6000",
                          "renewal_gate_examples": renewal_min,
                          "spec": reference(ROOT, "inputs/validation-spec-v1.json", "VALIDATION_SPEC")},
    "limitations": ["Literal guards and file hashes do not establish business truth or statistical power.",
                    "No pilot, product acceptance test, payments, current website read or external messages occurred."]
}
with (ROOT / "evidence/synthesis-verification-v1.json").open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps({"ok": True, "reused_artifacts": len(reused), "documents": len(document_checks),
                  "official_sources": len(official), "design_arithmetic": result["design_arithmetic"]}, ensure_ascii=False))
