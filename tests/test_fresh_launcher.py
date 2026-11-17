"""Технические guards launcher; эти тесты не имитируют fresh-host PASS."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location("fresh_m2", Path(__file__).resolve().parents[1] / "evaluation/run_fresh_host_m2.py")
fresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fresh)


class FreshLauncherTests(unittest.TestCase):
    def test_reconnect_noise_and_messages_do_not_keep_process_alive(self):
        monitor = fresh.Progress(0)
        monitor.stderr(b"WARN retrying sampling request (1/5)")
        monitor.event(json.dumps({"type": "error", "message": "Reconnecting... 1/5 (request timed out)"}), 40)
        monitor.event(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Подожду"}}), 59)
        self.assertEqual(monitor.stop_reason(61, 60, 5), "no_completed_action_timeout")
        self.assertEqual(monitor.completed_actions, 0)

    def test_success_resets_retry_window_but_failed_command_does_not(self):
        monitor = fresh.Progress(0)
        for _ in range(3):
            monitor.stderr(b"retrying sampling request")
        monitor.event(json.dumps({"type": "item.completed", "item": {"type": "command_execution", "exit_code": 1}}), 40)
        self.assertEqual(monitor.stop_reason(40, 60, 3), "transport_retries_without_completed_action")
        monitor.event(json.dumps({"type": "item.completed", "item": {"type": "command_execution", "exit_code": 0}}), 50)
        self.assertIsNone(monitor.stop_reason(100, 60, 3))
        self.assertEqual(monitor.completed_actions, 1)
        self.assertEqual(monitor.failed_commands, 1)
        self.assertEqual(monitor.total_stderr_retries, 3)

    def test_permission_denial_stops_without_waiting_for_retry_budget(self):
        monitor = fresh.Progress(0)
        monitor.stderr(b"connection failed (os error 10013)")
        self.assertEqual(monitor.stop_reason(1, 600, 5), "network_permission_error")

    def test_incremental_utf8_events_preserve_partial_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            line = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Продолжено"}}, ensure_ascii=False).encode("utf-8")
            cut = line.index("ж".encode("utf-8")) + 1
            path.write_bytes(line[:cut])
            reader = fresh.Lines(path)
            self.assertEqual(reader.read(), [])
            with path.open("ab") as stream:
                stream.write(line[cut:] + b"\n{\"type\":\"turn.completed\"}")
            self.assertEqual(reader.read(), [line])
            self.assertEqual(reader.read(final=True), [b'{"type":"turn.completed"}'])
            self.assertEqual(reader.read(final=True), [])

    def test_subsequent_load_failures_retain_cli_outcome(self):
        for failure, expected in (
            (fresh.subprocess.TimeoutExpired(["python", "project_state.py", "load"], 30), "timeout"),
            (OSError("искусственная ошибка доступа loader"), "io_error"),
        ):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                observed = {"exit_code": 0, "outcome": "exited", "observations": {"completed_actions": 2}}
                def fail_loader(*args):
                    # До запуска loader факт завершения CLI уже устойчиво записан.
                    pending = json.loads((output / "outcome.json").read_text(encoding="utf-8"))
                    self.assertEqual(pending["outcome"], "exited")
                    self.assertEqual(pending["subsequent_load_status"], "pending")
                    raise failure
                with mock.patch.object(fresh, "load_state", side_effect=fail_loader):
                    fresh.save_final_observation(observed, "python", output, "demo-002", output, {})
                saved = json.loads((output / "outcome.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["outcome"], "exited")
                self.assertEqual(saved["observations"]["completed_actions"], 2)
                self.assertEqual(saved["subsequent_load_status"], expected)
                self.assertIsNone(saved["subsequent_load_exit_code"])
                self.assertEqual(saved["subsequent_load_error"]["type"], type(failure).__name__)


if __name__ == "__main__":
    unittest.main()
