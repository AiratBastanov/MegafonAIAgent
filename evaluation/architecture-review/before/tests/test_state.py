"""Детерминированные проверки сохранения; не свидетельство поведения LLM."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "project_state.py"
spec = importlib.util.spec_from_file_location("project_state", SCRIPT)
state = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(state)


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "sample-case"
        self.project.mkdir()
        self.artifact = self.project / "evidence" / "values-v1.txt"
        self.artifact.parent.mkdir()
        self.artifact.write_text("Наблюдение: 5 из 20. Учебные данные.\n", encoding="utf-8")
        self.draft = {
            "schema_version": 1,
            "project_id": "sample-case",
            "objective": "Выбрать следующий проверяемый шаг продукта",
            "decision_question": "Изменять продукт или закрыть направление?",
            "stage": "research_complete",
            "completed": ["Входы прочитаны; арифметика проверена"],
            "unresolved_questions": ["Сколько стоит обслуживание?"],
            "pending_actions": ["Сопоставить варианты"],
            "next_action": "Сопоставить варианты по подтверждённым основаниям",
            "artifacts": [state.reference(self.project, "evidence/values-v1.txt", "A001")],
            "sources": [{"id": "S001", "version": 1, "artifact_ids": ["A001"], "synthetic": True}],
            "claims": [{
                "id": "C001", "kind": "source_fact", "text": "Источник сообщает 5 из 20",
                "evidence": [{"artifact_id": "A001", "locator": "строка 1", "source_id": "S001", "source_version": 1}],
                "derived_from": [], "synthetic": True,
            }],
            "decision": {"status": "proposed"},
        }

    def changed_draft(self):
        revised = copy.deepcopy(self.draft)
        path = self.project / "evidence" / "values-v2.txt"
        path.write_text("Исправлено: 7 из 20. Учебные данные.\n", encoding="utf-8")
        revised["artifacts"] = [state.reference(self.project, "evidence/values-v2.txt", "A002")]
        revised["sources"] = [{"id": "S001", "version": 2, "artifact_ids": ["A002"], "synthetic": True}]
        revised["claims"][0].update({
            "text": "Исправленный источник сообщает 7 из 20",
            "evidence": [{"artifact_id": "A002", "locator": "строка 1", "source_id": "S001", "source_version": 2}],
        })
        revised["stage"] = "needs_review"
        revised["next_action"] = "Пересчитать вывод после исправления"
        return revised

    def test_save_load_and_previous_keep_artifact_versions(self):
        first = state.save_state(self.project, self.draft)
        second = state.save_state(self.project, self.changed_draft())
        self.assertEqual(first["revision"], 1)
        self.assertEqual(second["revision"], 2)
        self.assertEqual(state.load_state(self.project)["stage"], "needs_review")
        previous = state.load_state(self.project, previous=True)
        self.assertEqual(previous, first)
        self.assertEqual(previous["sources"][0]["version"], 1)
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "Наблюдение: 5 из 20. Учебные данные.\n")
        self.assertTrue((self.project / "state/history/r000001.json").is_file())

    def test_failed_publication_keeps_current_and_previous_valid(self):
        first = state.save_state(self.project, self.draft)
        actual_replace = os.replace

        def fail_at_publish(src, dst):
            if Path(dst).name == "current.json":
                raise OSError("injected failed replacement")
            return actual_replace(src, dst)

        with patch.object(state.os, "replace", side_effect=fail_at_publish):
            with self.assertRaises(OSError):
                state.save_state(self.project, self.changed_draft())
        self.assertEqual(state.load_state(self.project), first)
        self.assertEqual(state.load_state(self.project, previous=True), first)
        warnings = state.inspect_state(self.project)["warnings"]
        self.assertTrue(any("временные" in warning for warning in warnings))
        self.assertTrue(any("неопубликованные" in warning for warning in warnings))
        # После исправления причины сбоя новый save не переиспользует r000002.
        third = state.save_state(self.project, self.changed_draft())
        self.assertEqual(third["revision"], 3)

    def test_invalid_candidate_does_not_touch_current_or_previous(self):
        first = state.save_state(self.project, self.draft)
        second = state.save_state(self.project, self.changed_draft())
        bad = copy.deepcopy(self.draft)
        bad["artifacts"][0]["path"] = "evidence/not-written.txt"
        with self.assertRaises(state.StateError):
            state.save_state(self.project, bad)
        self.assertEqual(state.load_state(self.project), second)
        self.assertEqual(state.load_state(self.project, previous=True), first)

    def test_truncated_current_is_visible_and_explicit_recovery_works(self):
        first = state.save_state(self.project, self.draft)
        state.save_state(self.project, self.changed_draft())
        current = self.project / "state/current.json"
        current.write_text('{"schema_version":', encoding="utf-8")
        with self.assertRaises(state.StateError):
            state.load_state(self.project)
        with self.assertRaises(state.StateError):
            state.save_state(self.project, self.draft)
        self.assertEqual(state.load_state(self.project, previous=True), first)
        self.assertEqual(state.recover_previous(self.project), first)
        self.assertEqual(state.load_state(self.project), first)
        self.assertEqual(len(list((self.project / "state").glob("replaced-current-*.json"))), 1)

    def test_valid_json_field_corruption_is_detected_by_state_checksum(self):
        state.save_state(self.project, self.draft)
        path = self.project / "state/current.json"
        edited = json.loads(path.read_text(encoding="utf-8"))
        edited["objective"] = "Незаметно подменённая цель"
        path.write_text(json.dumps(edited, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(state.StateError, "Контрольная сумма"):
            state.load_state(self.project)

    def test_changed_artifact_invalidates_current_but_not_prior_version(self):
        first = state.save_state(self.project, self.draft)
        state.save_state(self.project, self.changed_draft())
        (self.project / "evidence/values-v2.txt").write_text("Changed after save", encoding="utf-8")
        with self.assertRaisesRegex(state.StateError, "артефакта"):
            state.load_state(self.project)
        self.assertEqual(state.load_state(self.project, previous=True), first)

    def test_paths_reject_escape_absolute_and_service_state(self):
        for path in ("../outside.txt", "evidence/../../outside.txt", str(self.artifact), "C:relative.txt", "\\\\server\\share\\x"):
            with self.subTest(path=path), self.assertRaises(state.StateError):
                state.reference(self.project, path, "A999")
        state.save_state(self.project, self.draft)
        with self.assertRaises(state.StateError):
            state.reference(self.project, "state/current.json", "A999")

    def test_symlink_escape_is_rejected_when_host_permits_test_link(self):
        outside = self.base / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.project / "evidence/link.txt"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("Создание symlink недоступно в текущем Windows-профиле")
        with self.assertRaises(state.StateError):
            state.reference(self.project, "evidence/link.txt", "A999")

    def test_synthetic_propagation_reaches_recommendation(self):
        self.draft["claims"].extend([
            {"id": "C002", "kind": "hypothesis", "text": "Рабочая гипотеза", "evidence": [], "derived_from": ["C001"], "synthetic": True},
            {"id": "C003", "kind": "recommendation", "text": "Условное предложение", "evidence": [], "derived_from": ["C002"], "synthetic": False},
        ])
        with self.assertRaisesRegex(state.StateError, "C003"):
            state.validate_state(self.project, self.draft)
        self.draft["claims"][-1]["synthetic"] = True
        state.validate_state(self.project, self.draft)

    def test_synthetic_source_inferred_from_artifact_without_explicit_source(self):
        self.draft["claims"][0]["evidence"] = [{"artifact_id": "A001", "locator": "строка 1"}]
        self.draft["claims"][0]["synthetic"] = False
        with self.assertRaisesRegex(state.StateError, "синтетического"):
            state.validate_state(self.project, self.draft)

    def test_invalid_evidence_and_circular_claims_rejected(self):
        bad = copy.deepcopy(self.draft)
        bad["claims"][0]["evidence"][0]["source_version"] = 99
        with self.assertRaises(state.StateError):
            state.validate_state(self.project, bad)
        bad = copy.deepcopy(self.draft)
        bad["claims"][0]["derived_from"] = ["C001"]
        with self.assertRaisesRegex(state.StateError, "Циклическое"):
            state.validate_state(self.project, bad)

    def test_explicit_source_cannot_claim_an_unrelated_artifact(self):
        unrelated = self.project / "evidence/unrelated.txt"
        unrelated.write_text("Не является указанным источником", encoding="utf-8")
        self.draft["artifacts"].append(state.reference(self.project, "evidence/unrelated.txt", "A999"))
        self.draft["claims"][0]["evidence"][0]["artifact_id"] = "A999"
        with self.assertRaisesRegex(state.StateError, "не принадлежит"):
            state.validate_state(self.project, self.draft)

    def test_calculation_can_reference_its_versioned_original_but_not_other_bytes(self):
        original = self.draft["artifacts"][0]
        metadata = {
            "id": "S001", "version": 1, "original": original,
            "input_sha256": original["sha256"],
        }
        (self.project / "evidence/source.json").write_text(json.dumps(metadata), encoding="utf-8")
        self.draft["artifacts"].append(state.reference(self.project, "evidence/source.json", "AMETA"))
        self.draft["sources"][0]["artifact_ids"].append("AMETA")
        calculation = {
            "tool": "analyze_table", "source": {"id": "S001", "version": 1},
            "input": {"path": "inputs/earlier-location.txt", "sha256": original["sha256"]},
        }
        path = self.project / "evidence/calc.json"
        path.write_text(json.dumps(calculation), encoding="utf-8")
        self.draft["artifacts"].append(state.reference(self.project, "evidence/calc.json", "CALC"))
        self.draft["claims"][0]["evidence"][0]["artifact_id"] = "CALC"
        state.validate_state(self.project, self.draft)
        # Та же source ID/version при другом фактическом input hash неприемлема.
        calculation["input"]["sha256"] = "0" * 64
        path.write_text(json.dumps(calculation), encoding="utf-8")
        self.draft["artifacts"][-1] = state.reference(self.project, "evidence/calc.json", "CALC")
        with self.assertRaisesRegex(state.StateError, "не принадлежит"):
            state.validate_state(self.project, self.draft)

    def test_business_approval_cannot_be_invented_by_test_fixture(self):
        self.draft["decision"] = {"status": "accepted"}
        with self.assertRaises(state.StateError):
            state.validate_state(self.project, self.draft)
        self.draft["decision"]["human_confirmation"] = {
            "actor": "Симулированный участник", "authorized": True,
            "at": "2026-11-16T10:00:00+03:00", "evidence_artifact_id": "A001", "test_fixture": True,
        }
        with self.assertRaisesRegex(state.StateError, "Тестовое"):
            state.validate_state(self.project, self.draft)

    def test_new_approval_cannot_bypass_provenance_using_legacy_format(self):
        state.save_state(self.project, self.draft)
        self.draft['decision'] = {'status': 'accepted', 'human_confirmation': {
            'actor': 'Синтетический объект теста', 'authorized': True,
            'at': '2026-11-16T15:00:00+03:00', 'evidence_artifact_id': 'A001', 'test_fixture': False}}
        with self.assertRaisesRegex(state.StateError, 'format_version=2'):
            state.save_state(self.project, self.draft)

    def test_synthetic_marker_rejected_without_echoing_value(self):
        marker = "SYNTHETIC_" + "SECRET_DO_NOT_PUBLISH_872"
        self.artifact.write_text(marker, encoding="utf-8")
        self.draft["artifacts"][0]["sha256"] = hashlib.sha256(marker.encode()).hexdigest()
        with self.assertRaises(state.StateError) as caught:
            state.save_state(self.project, self.draft)
        self.assertNotIn(marker, str(caught.exception))
        self.assertFalse((self.project / "state/current.json").exists())

    def test_recovery_diagnostic_does_not_copy_corrupt_secret_bytes(self):
        state.save_state(self.project, self.draft)
        state.save_state(self.project, self.changed_draft())
        marker = "SYNTHETIC_" + "SECRET_RECOVERY_ONLY_149"
        corrupt = ('{"injected":"' + marker + '"').encode("utf-8")
        (self.project / "state/current.json").write_bytes(corrupt)
        state.recover_previous(self.project)
        diagnostics = list((self.project / "state").glob("replaced-current-*.json"))
        self.assertEqual(len(diagnostics), 1)
        diagnostic = json.loads(diagnostics[0].read_text(encoding="utf-8"))
        self.assertFalse(diagnostic["raw_preserved"])
        self.assertEqual(diagnostic["size_bytes"], len(corrupt))
        self.assertEqual(diagnostic["sha256"], hashlib.sha256(corrupt).hexdigest())
        for path in (self.project / "state").rglob("*.json"):
            self.assertNotIn(marker, path.read_text(encoding="utf-8"))

    def test_size_guard_and_nonfinite_values(self):
        with self.assertRaisesRegex(state.StateError, "max_bytes"):
            state.reference(self.project, "evidence/values-v1.txt", "A999", max_bytes=1)
        self.draft["unobserved_cost"] = float("nan")
        with self.assertRaises(state.StateError):
            state.validate_state(self.project, self.draft)

    def test_invalid_types_are_validation_errors(self):
        cases = [
            ("kind", ["source_fact"]), ("evidence", [{"artifact_id": [], "locator": "строка 1"}]),
        ]
        for field, value in cases:
            bad = copy.deepcopy(self.draft)
            bad["claims"][0][field] = value
            with self.subTest(field=field), self.assertRaises(state.StateError):
                state.validate_state(self.project, bad)
        bad = copy.deepcopy(self.draft)
        bad["decision"] = {"status": []}
        with self.assertRaises(state.StateError):
            state.validate_state(self.project, bad)

    def test_cli_corruption_reports_error_instead_of_silent_fallback(self):
        state.save_state(self.project, self.draft)
        state.save_state(self.project, self.changed_draft())
        (self.project / "state/current.json").write_text("{", encoding="utf-8")
        process = subprocess.run(
            [sys.executable, str(SCRIPT), "load", "--project", str(self.project)],
            capture_output=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, check=False,
        )
        self.assertEqual(process.returncode, 2)
        self.assertFalse(json.loads(process.stderr)["ok"])
        self.assertIn("--previous", json.loads(process.stderr)["next_step"])
        self.assertEqual(process.stdout, "")

    def test_cli_uses_utf8_even_with_windows_legacy_io_encoding(self):
        self.draft["objective"] = "Наблюдение → проверяемое решение"
        state.save_state(self.project, self.draft)
        process = subprocess.run(
            [sys.executable, str(SCRIPT), "load", "--project", str(self.project)],
            capture_output=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "cp1251"}, check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["state"]["objective"], self.draft["objective"])


if __name__ == "__main__":
    unittest.main()
