"""Read-only access to the project's case and result files."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"


class DataReadError(RuntimeError):
    """An existing project data file could not be parsed."""


def _json(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise DataReadError(f"Cannot read {path.name}: {exc}") from exc


def _value(raw: str | None) -> Any:
    if raw is None or raw == "":
        return None
    if raw.lower() in {"true", "false"}:
        return raw.lower() == "true"
    try:
        return float(raw) if any(char in raw.lower() for char in ".e") else int(raw)
    except ValueError:
        return raw


def _csv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return [{key: _value(value) for key, value in row.items()} for row in csv.DictReader(handle)]
    except (OSError, csv.Error) as exc:
        raise DataReadError(f"Cannot read {path.name}: {exc}") from exc


def _csv_if_present(path: Path) -> list[dict[str, Any]]:
    return _csv(path) if path.exists() else []


def _all_cases() -> list[dict[str, Any]]:
    rows = _json(DATA / "evaluation_cases_B.json")
    if not isinstance(rows, list):
        raise DataReadError("evaluation_cases_B.json must contain an array")
    return rows


def _public_case(case: dict[str, Any], *, detail: bool = False) -> dict[str, Any]:
    keys = ["case_id", "source", "evaluation_tier", "negative_case", "design_purpose", "input_summary"]
    if detail:
        keys.insert(4, "trials")
    return {key: case.get(key) for key in keys}


def list_cases(*, tier: str = "all", negative_case: bool | None = None) -> list[dict[str, Any]]:
    return [
        _public_case(case)
        for case in _all_cases()
        if (tier == "all" or case.get("evaluation_tier") == tier)
        and (negative_case is None or case.get("negative_case") is negative_case)
    ]


def get_case(case_id: str) -> dict[str, Any] | None:
    case = next((item for item in _all_cases() if item.get("case_id") == case_id), None)
    return _public_case(case, detail=True) if case else None


def get_case_and_answer(case_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    case = next((item for item in _all_cases() if item.get("case_id") == case_id), None)
    answers = _json(DATA / "expected_outcomes_B.json")
    answer = next((item for item in answers if item.get("case_id") == case_id), None)
    return (case, answer) if case and answer else None


def read_evidence() -> dict[str, Any]:
    d5_models: list[dict[str, Any]] = []
    for summary_path in sorted((RESULTS / "live").glob("*/scored_reviewed/summary.json")):
        summary = _json(summary_path)
        policies = summary.get("by_policy_model") or []
        if not policies:
            continue
        item = policies[0]
        run_rows = _csv_if_present(summary_path.with_name("runs.csv"))
        sources = sorted({str(row["cost_source"]) for row in run_rows if row.get("cost_source")})
        d5_models.append({
            "model": item.get("model"),
            "runs": item.get("runs"),
            "final_pass_rate": item.get("final_pass_rate"),
            "negative_final_pass_rate": item.get("negative_final_pass_rate"),
            "unsafe_booking_attempts": summary.get("negative_booking_attempts"),
            "tokens_in": sum(row.get("tokens_in") or 0 for row in run_rows),
            "tokens_out": sum(row.get("tokens_out") or 0 for row in run_rows),
            "cost_usd": summary.get("total_cost_usd"),
            "cost_source": ",".join(sources) or None,
            "mean_turns": summary.get("mean_turns"),
        })
    d7_path = RESULTS / "d7_failure_results.json"
    return {
        "d2": {"variants": _csv_if_present(RESULTS / "d2_experiment_summary.csv")},
        "d4": {"policies": _csv_if_present(RESULTS / "d4_policy_model_summary.csv")},
        "d5": {"models": d5_models},
        "d7": _json(d7_path) if d7_path.exists() else None,
    }


def _live_csv(name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((RESULTS / "live").glob(f"*/scored_reviewed/{name}")):
        rows.extend(_csv(path))
    return rows


def read_audit_runs(
    *, case_id: str | None = None, model: str | None = None,
    passed: bool | None = None, negative_case: bool | None = None, limit: int = 100,
) -> list[dict[str, Any]]:
    rows = _live_csv("runs.csv")
    return [
        row for row in rows
        if (case_id is None or row.get("case_id") == case_id)
        and (model is None or row.get("model") == model)
        and (passed is None or row.get("passed") is passed)
        and (negative_case is None or row.get("negative_case") is negative_case)
    ][:limit]


def read_tool_calls(run_id: str) -> list[dict[str, Any]] | None:
    run_ids = {row.get("run_id") for row in _live_csv("runs.csv")}
    if run_id not in run_ids:
        return None
    keys = ["turn", "tool_name", "descriptor_version", "observation_tokens", "observation_chars", "latency_ms", "ok", "error_code"]
    return [
        {key: row.get(key) for key in keys}
        for row in _live_csv("tool_calls.csv") if row.get("run_id") == run_id
    ]
