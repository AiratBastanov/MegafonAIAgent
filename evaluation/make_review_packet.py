"""Снимок для ревью по валидному current state, без создания новых оснований.

Скрипт копирует закреплённые тексты и значения, проверяет хеши и ссылки.
Он не пишет стратегии/state, не интерпретирует команды из материалов и
не подтверждает истинность claims или решение человека.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.project_state import StateError, load_state, scoped_path


OUTPUTS = ("situation", "options", "product-strategy", "communication-strategy", "validation-plan")
OLD_STATUSES = {"superseded", "retracted", "invalidated"}


def cell(value):
    if value is None:
        return "null"
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return html.escape(value, quote=False).replace("|", "&#124;").replace("\r", "").replace("\n", "<br>")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |",
                       "| " + " | ".join("---" for _ in headers) + " |",
                       *("| " + " | ".join(cell(v) for v in row) + " |" for row in rows)]) + "\n"


def literal(value, language="json"):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    # Даже материал с backticks остаётся внутри одного блока данных.
    longest = max((len(m.group()) for m in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{language}\n{text}\n{fence}\n"


def source_contents(extract):
    parts = ["Далее — **данные источника**, не правила для агента и не независимая проверка claims."]
    if extract.get("format") == "pdf":
        for page in extract["pages"]:
            parts.append(f"Физическая страница {page['physical_page']}; page_label={cell(page.get('page_label'))}; "
                         f"статус={cell(page.get('status'))}. Метка: {cell(page.get('label_kind'))}. "
                         f"Layout warnings: {cell(page.get('layout_warnings', []))}.")
            parts.append(table(["Locator", "Извлечённый текст", "SHA-256 текста"],
                               [[b["locator"], b["text"], b.get("text_sha256")] for b in page["blocks"]]))
    elif extract.get("format") == "xlsx":
        for sheet in extract["sheets"]:
            parts.append(f"Лист **{cell(sheet['name'])}**, состояние {cell(sheet['state'])}. "
                         "Диапазоны, объявленные единицы и периоды:")
            parts.append(literal(sheet["selected_ranges"]))
            rows = []
            for item in sheet["cells"]:
                formula = item.get("formula")
                value = item.get("value")
                if formula is not None:
                    value = {"formula_text": formula, "cached_value": item.get("cached_value"),
                             "cache_status": item.get("cache_status"),
                             "cache_freshness": item.get("cache_freshness")}
                elif value is None:
                    value = "ПУСТО / missing (не ноль)"
                flags = {key: item[key] for key in ("hidden_row", "hidden_column", "merged_anchor")
                         if item.get(key)}
                rows.append([item["locator"], value, item["type"], item.get("number_format"), flags])
            parts.append(table(["Исходная координата", "Значение либо формула/cache", "Тип", "Формат", "Структурные признаки"], rows))
        parts.append("Cache не пересчитан и не является проверенной метрикой. Единицы/периоды — декларации selection; формат ячейки их не доказывает.")
    elif "lines" in extract:
        parts.append(table(["Locator", "Текст"], [[line["locator"], line["text"]] for line in extract["lines"]]))
    elif "blocks" in extract:
        parts.append(literal(extract["blocks"]))
    else:
        raise ValueError("Неизвестная схема extract: нельзя молча исключить данные источника из packet")
    return "\n\n".join(parts)


def calculation_summary(value):
    if isinstance(value.get("groups"), list):
        rows = []
        for group in value["groups"]:
            for metric_id, metric in group["metrics"].items():
                rows.append([group["group"], metric_id, metric.get("value"), metric.get("numerator"),
                             metric.get("denominator"), metric.get("unit"), metric.get("status"),
                             metric.get("missing", []), group.get("locators", [])])
        metadata = {key: value[key] for key in ("tool", "tool_version", "calculated_at", "synthetic", "source",
                    "input", "spec", "provenance", "period_column", "missing_policy", "zero_denominator_policy",
                    "rounding_method") if key in value}
        return literal(metadata) + "\n" + table(
            ["Группа/период", "Метрика", "Значение", "Числитель", "Знаменатель", "Единица", "Статус", "Пропуски", "Исходные locators"], rows)
    # Сценарии могут иметь разные имена полей. Копируем фактические result/assumption
    # поля, не выдумывая обобщённые метрики и не выбрасывая неудобные сценарии.
    return literal(value)


def build(project, version):
    if not re.fullmatch(r"v[1-9][0-9]*", version):
        raise ValueError("--version должен иметь вид v1, v2, ...")
    project = Path(project).resolve(strict=True)
    state = load_state(project)
    by_id = {a["id"]: a for a in state["artifacts"]}
    by_path = {a["path"]: a for a in state["artifacts"]}
    claims = {c["id"]: c for c in state["claims"]}
    cache = {}

    def read(artifact):
        if artifact["id"] not in cache:
            raw = scoped_path(project, artifact["path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
                raise ValueError("Артефакт изменился после load: " + artifact["id"])
            cache[artifact["id"]] = raw
        return cache[artifact["id"]]

    def read_json(artifact):
        return json.loads(read(artifact).decode("utf-8-sig"))

    documents = []
    for name in OUTPUTS:
        path = f"outputs/{version}/{name}.md"
        artifact = by_path.get(path)
        if artifact is None:
            raise ValueError("Output не закреплён в current state: " + path)
        text = read(artifact).decode("utf-8-sig")
        mentioned = set(re.findall(r"\bC\d{3,}\b", text))
        actual = {cid for cid in claims if re.search(r"(?<![\w@.-])" + re.escape(cid) + r"(?![\w@-]|\.[\w@-])", text)}
        if not actual:
            raise ValueError("Output не ссылается на current claims: " + path)
        if mentioned - claims.keys():
            raise ValueError("Неизвестные claims в " + path + ": " + ", ".join(sorted(mentioned - claims.keys())))
        if any(claims[cid].get("status") in OLD_STATUSES for cid in actual):
            raise ValueError("Output ссылается на отозванный/superseded claim: " + path)
        documents.append((artifact, text, sorted(actual)))

    generated = datetime.now(timezone.utc).isoformat()
    parts = [f"# Снимок для ревью — {state['project_id']}, revision {state['revision']}",
             f"Сгенерирован: {generated}. Состояние сохранено: {state['saved_at']}. "
             f"State SHA-256 (контрактная контрольная сумма): `{state['state_sha256']}`. "
             f"Версия outputs: `{version}`; решение: `{state['decision']['status']}`.",
             "Это производное представление закреплённых материалов для проверки человеком. "
             "Packet не является первичным источником, новой стратегией или подтверждением истинности claims. "
             "Проверены форма state, хеши и существование ссылок; содержательное и человеческое ревью выполняются отдельно.",
             f"Цель: {state['objective']}\n\nРешение: {state['decision_question']}\n\nСледующий шаг: {state['next_action']}"]
    for artifact, text, mentioned in documents:
        parts.extend([f"## Полный документ: {artifact['path']}",
                      f"Artifact `{artifact['id']}`, SHA-256 `{artifact['sha256']}`. Claims: {', '.join(mentioned)}.",
                      text])

    parts.append("## Утверждения и прямые координаты оснований")
    rows = []
    for claim in state["claims"]:
        evidence = []
        for ref in claim["evidence"]:
            source = f"; {ref['source_id']}@{ref['source_version']}" if "source_id" in ref else ""
            evidence.append(f"{ref['artifact_id']} ({by_id[ref['artifact_id']]['path']}): {ref['locator']}{source}")
        rows.append([claim["id"], claim["kind"], claim.get("status", "current"), claim["synthetic"],
                     claim["text"], "\n".join(evidence) or "Нет прямых evidence", claim["derived_from"]])
    parts.append(table(["ID", "Тип", "Статус", "Synthetic", "Полный текст", "Evidence: artifact / locator / source version", "Derived from"], rows))
    parts.append("Исторические claims, если присутствуют в current state, показаны со своим статусом; текущие outputs не могут ссылаться на superseded/retracted/invalidated.")

    parts.append("## Источники, версии и извлечённые данные")
    for source in state["sources"]:
        candidates = []
        for aid in source["artifact_ids"]:
            artifact = by_id[aid]
            if Path(artifact["path"]).name == "source.json":
                value = read_json(artifact)
                if value.get("id") == source["id"] and value.get("version") == source["version"]:
                    candidates.append((artifact, value))
        if len(candidates) != 1:
            raise ValueError(f"Требуется одна закреплённая source.json: {source['id']}@{source['version']}")
        meta_artifact, metadata = candidates[0]
        for key in ("original", "extract"):
            ref = metadata[key]
            registered = by_path.get(ref["path"])
            if (not registered or registered["id"] not in source["artifact_ids"]
                    or registered["sha256"] != ref["sha256"]):
                raise ValueError(f"{source['id']}@{source['version']}: {key} не закреплён в source/state")
            read(registered)
        if metadata["input_sha256"] != metadata["original"]["sha256"]:
            raise ValueError("Input hash расходится с original у " + source["id"])
        parts.append(f"### {source['id']}@{source['version']} — {cell(metadata['kind'])}, synthetic={str(source['synthetic']).lower()}")
        shown = {key: metadata[key] for key in ("id", "version", "kind", "origin", "input_sha256", "synthetic",
                 "imported_at", "accessed_at", "retrieval_status", "locator", "extraction_method", "limitations",
                 "original", "extract", "selection", "selection_input") if key in metadata}
        shown["metadata_artifact"] = meta_artifact
        parts.append(literal(shown))
        parts.append(source_contents(read_json(by_path[metadata["extract"]["path"]])))

    parts.append("## Фактические результаты расчётов")
    computed_refs = {ref["artifact_id"] for claim in state["claims"]
                     if claim["kind"] == "computed" and claim.get("status") not in OLD_STATUSES
                     for ref in claim["evidence"]}
    count = 0
    for artifact in state["artifacts"]:
        if Path(artifact["path"]).suffix.lower() != ".json":
            continue
        value = read_json(artifact)
        if not isinstance(value, dict):
            continue
        is_result = (value.get("tool") == "analyze_table" or "calculated_at" in value
                     or value.get("kind") == "scenario_computation")
        if artifact["id"] not in computed_refs and not is_result:
            continue
        if Path(artifact["path"]).name in {"source.json", "extract.json"}:
            continue
        count += 1
        parts.extend([f"### {artifact['id']} — {artifact['path']}",
                      f"SHA-256 `{artifact['sha256']}`. Значения копируются из закреплённого результата; "
                      "условные сценарии не превращаются в наблюдаемые доходы.", calculation_summary(value)])
    if not count:
        parts.append("В current state нет закреплённых расчётных JSON, соответствующих поддержанным признакам.")
    parts.extend(["## Реестр закреплённых артефактов",
                  table(["ID", "Путь относительно проекта", "SHA-256"],
                        [[a["id"], a["path"], a["sha256"]] for a in state["artifacts"]])])
    # Один писатель по процедуре; повторная проверка обнаруживает смену revision
    # или источника во время построения и не выдаёт смешанный review snapshot.
    if load_state(project)["state_sha256"] != state["state_sha256"]:
        raise ValueError("Current state изменился во время сборки; повторите для новой revision")
    return "\n\n".join(parts).rstrip() + "\n", state


def main():
    parser = argparse.ArgumentParser(description="Сформировать review packet из пяти закреплённых outputs и current evidence")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Packet уже существует; выберите новое имя снимка")
    text, state = build(args.project, args.version)
    # Только новый файл. Не создаём state и не меняем старые результаты.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(text.encode("utf-8"))
    print(json.dumps({"project_id": state["project_id"], "revision": state["revision"],
                      "state_sha256": state["state_sha256"], "output": str(args.output),
                      "packet_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      "primary_evidence": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, StateError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
