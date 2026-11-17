"""Один новый Codex exec для проверки продолжения; не агентный цикл.

Повторные подключения не сбрасывают таймер полезного технического прогресса.
Успешный tool event ещё не доказывает содержательность результата: её проверяет
отдельный аудит артефактов и сохранённого состояния. Настройки/auth не читаются.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Progress:
    """Счётчики наблюдений; не оценка правильности или пользы стратегии."""
    def __init__(self, tick):
        self.last_progress = tick
        self.completed_actions = 0
        self.failed_commands = 0
        self.agent_messages = 0
        self.event_retries = self.stderr_retries = 0
        self.total_event_retries = self.total_stderr_retries = 0
        self.network_denied = False
        self.thread_id = None
        self.turn_completed = False
        self.usage = None
        self.invalid_event_lines = 0

    def event(self, line, tick):
        try:
            event = json.loads(line)
        except (ValueError, UnicodeError):
            self.invalid_event_lines += 1
            return
        if not isinstance(event, dict):
            self.invalid_event_lines += 1
            return
        if event.get("type") == "thread.started":
            self.thread_id = event.get("thread_id")
        if event.get("type") == "turn.completed":
            self.turn_completed = True
            self.usage = event.get("usage")
        message = str(event.get("message", "")).lower()
        if event.get("type") == "error" and any(x in message for x in
                ("reconnect", "timed out", "stream disconnected", "tls")):
            self.event_retries += 1
            self.total_event_retries += 1
        if "os error 10013" in message:
            self.network_denied = True
        if event.get("type") != "item.completed":
            return
        item = event.get("item", {})
        if not isinstance(item, dict):
            self.invalid_event_lines += 1
            return
        kind = item.get("type")
        if kind == "agent_message":
            self.agent_messages += 1
        if kind == "command_execution" and item.get("exit_code") != 0:
            self.failed_commands += 1
        success = ((kind == "command_execution" and item.get("exit_code") == 0)
                   or (kind in {"file_change", "mcp_tool_call", "tool_call"}
                       and item.get("status") == "completed"))
        if success:
            self.last_progress = tick
            self.completed_actions += 1
            self.event_retries = self.stderr_retries = 0

    def stderr(self, line):
        text = line.decode("utf-8", errors="replace").lower()
        if "os error 10013" in text:
            self.network_denied = True
        if "retrying sampling request" in text or "retrying request" in text:
            self.stderr_retries += 1
            self.total_stderr_retries += 1

    def stop_reason(self, tick, timeout, retry_limit):
        if self.network_denied:
            return "network_permission_error"
        # stderr и JSON могут описывать один retry: не складываем их.
        if max(self.event_retries, self.stderr_retries) >= retry_limit:
            return "transport_retries_without_completed_action"
        if tick - self.last_progress >= timeout:
            return "no_completed_action_timeout"
        return None


class Lines:
    def __init__(self, path):
        self.path, self.offset, self.pending = path, 0, b""

    def read(self, final=False):
        with self.path.open("rb") as stream:
            stream.seek(self.offset)
            fresh = stream.read()
        self.offset += len(fresh)
        pieces = (self.pending + fresh).split(b"\n")
        self.pending = pieces.pop()
        if final and self.pending:
            pieces.append(self.pending)
            self.pending = b""
        return [line for line in pieces if line.strip()]


def run_capture(cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=30)


def environment(python, requirements):
    pins = {}
    for raw in requirements.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)", line)
        if not match:
            raise ValueError("requirements должен содержать точные name==version pins")
        pins[match[1]] = match[2]
    probe = ("import importlib.metadata as m,json,sys; "
             "print(json.dumps({'executable':sys.executable,'python':sys.version,"
             "'packages':{n:m.version(n) for n in sys.argv[1:]}}))")
    result = run_capture([str(python), "-c", probe, *pins])
    if result.returncode:
        raise ValueError("Выбранный Python не содержит dependencies; выполните локальный pip install -r requirements.txt")
    record = json.loads(result.stdout)
    if record["packages"] != pins:
        raise ValueError("Версии выбранного Python не совпадают с requirements.txt")
    record["requirements_sha256"] = hashlib.sha256(requirements.read_bytes()).hexdigest()
    record["requirements_path"] = str(requirements)
    record["wrapper_python"] = sys.executable
    return record


def stop_owned(proc):
    """Только PID, полученный этим Popen; обхода ошибок прав нет."""
    if proc.poll() is not None:
        return {"method": "already_exited"}
    try:
        if os.name == "nt":
            result = run_capture(["taskkill", "/PID", str(proc.pid), "/T", "/F"])
            record = {"method": "taskkill_own_pid_tree", "returncode": result.returncode,
                      "stdout": result.stdout, "stderr": result.stderr}
        else:
            proc.terminate()
            record = {"method": "terminate_own_pid"}
        proc.wait(timeout=15)
        return record
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"method": "cleanup_failed", "error_type": type(exc).__name__,
                "pid": proc.pid, "action": "Проверить только этот собственный процесс; ограничения не обходить"}


def load_state(python, workspace, project_id, destination, env):
    result = run_capture([str(python), "scripts/project_state.py", "load", "--project",
                          "projects/" + project_id], cwd=workspace, env=env)
    destination.write_text(result.stdout, encoding="utf-8")
    destination.with_suffix(".stderr.txt").write_text(result.stderr, encoding="utf-8")
    return result.returncode


def save_final_observation(result, python, workspace, project_id, output, env):
    """Ошибка отдельного loader не должна уничтожать наблюдение о самом CLI."""
    result["subsequent_load_exit_code"] = None
    result["subsequent_load_status"] = (
        "pending" if result["exit_code"] is not None else "not_attempted_process_running")
    write_json(output / "outcome.json", result)
    if result["exit_code"] is None:
        return
    try:
        code = load_state(python, workspace, project_id, output / "subsequent-load.json", env)
        result["subsequent_load_exit_code"] = code
        result["subsequent_load_status"] = "completed" if code == 0 else "validation_failed"
    except (OSError, subprocess.TimeoutExpired) as error:
        result["subsequent_load_status"] = (
            "timeout" if isinstance(error, subprocess.TimeoutExpired) else "io_error")
        result["subsequent_load_error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        write_json(output / "outcome.json", result)


def main():
    parser = argparse.ArgumentParser(description="Один новый Codex exec с записью фактов продолжения")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True, help="Проверенный interpreter; venv не копируется")
    parser.add_argument("--project-id", default="demo-002")
    parser.add_argument("--timeout", type=int, default=600, help="Секунды без успешно завершённого действия")
    parser.add_argument("--transport-retry-limit", type=int, default=5)
    args = parser.parse_args()
    workspace, output, python = args.workspace.resolve(strict=True), args.output.resolve(), args.python.resolve(strict=True)
    if output == workspace or output.is_relative_to(workspace):
        raise ValueError("Журнал проверки должен находиться вне чистого workspace")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.project_id) or args.timeout <= 0 or args.transport_retry_limit <= 0:
        raise ValueError("Некорректный ID или неположительный технический предел")
    request = args.request.read_text(encoding="utf-8-sig").strip()
    if not request:
        raise ValueError("Запрос пуст")
    output.mkdir(parents=True, exist_ok=False)
    env_info = environment(python, workspace / "requirements.txt")
    write_json(output / "environment.json", env_info)
    codex = shutil.which("codex")
    if not codex:
        raise ValueError("codex отсутствует в PATH")
    for suffix in ("version", "help"):
        preflight = run_capture([codex, "--" + suffix])
        (output / ("codex-" + suffix + ".txt")).write_text(preflight.stdout + preflight.stderr, encoding="utf-8")
        if preflight.returncode:
            raise ValueError("Не удалось проверить установленный Codex CLI")
    help_result = run_capture([codex, "exec", "--help"])
    (output / "codex-exec-help.txt").write_text(help_result.stdout + help_result.stderr, encoding="utf-8")
    needed = ("--cd", "--sandbox", "--skip-git-repo-check", "--ephemeral", "--json", "--output-last-message")
    if help_result.returncode or any(flag not in help_result.stdout for flag in needed):
        raise ValueError("Установленный exec не подтвердил необходимые флаги; запуск остановлен")
    env = os.environ.copy()
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
                "MEGAFON_PROJECT_PYTHON": str(python),
                "PATH": str(python.parent) + os.pathsep + env.get("PATH", "")})
    if load_state(python, workspace, args.project_id, output / "starting-load.json", env):
        raise ValueError("Стартовый load не прошёл; модель не запущена")
    cmd = [codex, "exec", "--cd", str(workspace), "--sandbox", "workspace-write",
           "--skip-git-repo-check", "--ephemeral", "--json", "--color", "never",
           "--output-last-message", str(output / "last-message.txt"), request]
    tick = time.monotonic()
    launch = {"started_at": now(), "argv": cmd, "request": request, "new_session": True,
              "prior_transcript_supplied": False, "timeout_seconds_without_completed_action": args.timeout,
              "transport_retry_limit": args.transport_retry_limit, "environment": env_info,
              "environment_overrides": ["PYTHONIOENCODING=utf-8", "PYTHONUTF8=1", "MEGAFON_PROJECT_PYTHON", "PATH prepend selected Python"]}
    write_json(output / "launch.json", launch)
    monitor = Progress(tick)
    with (output / "events.jsonl").open("wb") as out, (output / "stderr.txt").open("wb") as err:
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                    cwd=workspace, env=env,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except OSError as error:
            result = {**launch, "ended_at": now(), "elapsed_seconds": round(time.monotonic() - tick, 3),
                      "outcome": "process_start_failed", "error_type": type(error).__name__,
                      "error": str(error), "exit_code": None, "subsequent_load_exit_code": None}
            write_json(output / "outcome.json", result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2
        launch["pid"] = proc.pid
        write_json(output / "launch.json", launch)
        events, errors = Lines(output / "events.jsonl"), Lines(output / "stderr.txt")
        outcome, cleanup = "exited", None
        try:
            while proc.poll() is None:
                for line in events.read():
                    monitor.event(line, time.monotonic())
                for line in errors.read():
                    monitor.stderr(line)
                reason = monitor.stop_reason(time.monotonic(), args.timeout, args.transport_retry_limit)
                if reason:
                    outcome, cleanup = reason, stop_owned(proc)
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            outcome, cleanup = "launcher_interrupted", stop_owned(proc)
        except OSError as error:
            outcome, cleanup = "launcher_io_error", stop_owned(proc)
            cleanup["launcher_error_type"] = type(error).__name__
        for line in events.read(final=True):
            monitor.event(line, time.monotonic())
        for line in errors.read(final=True):
            monitor.stderr(line)
    result = {**launch, "ended_at": now(), "elapsed_seconds": round(time.monotonic() - tick, 3),
              "exit_code": proc.poll(), "outcome": outcome, "cleanup": cleanup,
              "observations": {key: value for key, value in vars(monitor).items() if key != "last_progress"},
              "seconds_since_completed_action": round(time.monotonic() - monitor.last_progress, 3),
              "model_identity": None, "charges": None,
              "substantive_continuation_status": "requires_independent_artifact_and_state_audit"}
    # Это отдельный процесс загрузчика после завершения CLI, а не запись state родителем.
    save_final_observation(result, python, workspace, args.project_id, output, env)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if proc.returncode == 0 and result.get("subsequent_load_exit_code") == 0 else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
