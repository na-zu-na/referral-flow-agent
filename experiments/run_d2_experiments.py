#!/usr/bin/env python3
"""Run the controlled D2(b)/D2(c) comparisons and write result tables."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import run_case  # noqa: E402
from config import RunConfig  # noqa: E402
from evaluation.harness import run_log_row, write_run_logs  # noqa: E402
from prompt import prompt_audit  # noqa: E402


VARIANTS = (
    ("descriptor_v1_parallel", "v1", "parallel"),
    ("descriptor_v2_parallel", "v2", "parallel"),
    ("callmode_v2_sequential", "v2", "sequential"),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("scripted", "live"), default="scripted")
    parser.add_argument("--model", action="append", help="Repeat for each live OpenRouter model.")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--tier", choices=("core", "extended", "all"), default="core")
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--output-prefix", default="d2_experiment")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.trials < 1:
        raise SystemExit("--trials must be positive")
    if args.backend == "live" and not args.model:
        raise SystemExit("Live experiments require at least one --model.")

    cases = _selected_cases(args.tier, args.case_ids)
    expected = _load_json(ROOT / "data/expected_outcomes_B.json")
    expected_by_id = {item["case_id"]: item for item in expected}
    models = args.model if args.backend == "live" else [None]
    runs: list[dict[str, Any]] = []
    log_results: list[dict[str, Any]] = []

    for model in models:
        for variant, descriptor_version, call_mode in VARIANTS:
            config = RunConfig.from_env(
                backend=args.backend,
                model=model,
                descriptor_version=descriptor_version,
                call_mode=call_mode,
                temperature=0.0,
            )
            for case in cases:
                for trial in range(1, args.trials + 1):
                    record = run_case(
                        case["case_id"],
                        config,
                        approve=_approve_simulated_booking,
                    )
                    expected = expected_by_id[case["case_id"]]
                    passed = _passes(record, expected)
                    actual_decision = (record.get("final") or {}).get("decision")
                    failure_reason = "" if passed else "expected_outcome_mismatch"
                    log_item = {
                        "case_id": case["case_id"],
                        "trial": trial,
                        "negative_case": case["negative_case"],
                        "expected_decision": expected["expected_decision"],
                        "actual_decision": actual_decision,
                        "passed": passed,
                        "failure_reason": failure_reason,
                        "record": record,
                    }
                    log_results.append(log_item)
                    no_booking = not any(
                        observation["name"] == "book_slot"
                        and observation["result"].get("ok") is True
                        for observation in record["observations"]
                    )
                    runs.append(
                        {
                            "variant": variant,
                            **run_log_row(log_item),
                            "model": model or "scripted",
                            "call_mode": call_mode,
                            "negative_guardrail_passed": (
                                passed and no_booking if case["negative_case"] else None
                            ),
                            "final": record["final"],
                            "iterations": record["iterations"],
                            "tool_calls": [
                                {"turn": call["turn"], "name": call["name"]}
                                for call in record["tool_calls"]
                            ],
                            "observations": [
                                {
                                    "turn": observation["turn"],
                                    "name": observation["name"],
                                    "ok": observation["result"].get("ok"),
                                    "return_characters": observation["return_characters"],
                                    "return_tokens_estimated_chars_div_4": observation[
                                        "return_tokens_estimated_chars_div_4"
                                    ],
                                }
                                for observation in record["observations"]
                            ],
                            "error": record["error"],
                        }
                    )

    output_dir = ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    prefix = output_dir / args.output_prefix
    summaries = _summaries(runs)
    tool_rows = _tool_return_summaries(runs)
    _write_json(prefix.with_name(prefix.name + "_runs.json"), runs)
    _write_csv(prefix.with_name(prefix.name + "_summary.csv"), summaries)
    _write_csv(prefix.with_name(prefix.name + "_tool_returns.csv"), tool_rows)
    write_run_logs(log_results, output_dir / args.output_prefix)
    print(json.dumps(summaries, indent=2))
    return 0 if all(row["pass_rate"] == 1.0 for row in summaries) else 1


def _selected_cases(tier: str, requested: list[str] | None) -> list[dict[str, Any]]:
    cases = _load_json(ROOT / "data/evaluation_cases_B.json")
    selected = cases if tier == "all" else [case for case in cases if case["evaluation_tier"] == tier]
    if requested:
        wanted = set(requested)
        selected = [case for case in selected if case["case_id"] in wanted]
        missing = wanted - {case["case_id"] for case in selected}
        if missing:
            raise SystemExit("Unknown or out-of-tier case ids: " + ", ".join(sorted(missing)))
    return selected


def _passes(record: dict[str, Any], expected: dict[str, Any]) -> bool:
    final = record.get("final")
    if not isinstance(final, dict) or final.get("decision") != expected["expected_decision"]:
        return False
    if final["decision"] == "book":
        return final.get("booked") == expected.get("booked")
    if final["decision"] == "request_information":
        return final.get("missing") == expected.get("missing")
    return final.get("trigger") == expected.get("trigger")


def _approve_simulated_booking(event: dict[str, Any]) -> bool:
    return (
        event.get("type") == "confirmation_required"
        and event.get("call", {}).get("name") == "book_slot"
    )


def _summaries(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        groups[(run["model"], run["variant"])].append(run)

    rows = []
    for (model, variant), group in sorted(groups.items()):
        first = group[0]
        negative = [run for run in group if run["negative_case"]]
        audit = prompt_audit(
            first["descriptor_version"],
            first["call_mode"],
            first["prompt_version"],
        )
        return_tokens = [
            observation["return_tokens_estimated_chars_div_4"]
            for run in group
            for observation in run["observations"]
        ]
        rows.append(
            {
                "variant": variant,
                "backend": first["backend"],
                "model": model,
                "descriptor_version": first["descriptor_version"],
                "call_mode": first["call_mode"],
                "runs": len(group),
                "passed": sum(run["passed"] for run in group),
                "pass_rate": round(mean(run["passed"] for run in group), 6),
                "negative_runs": len(negative),
                "negative_guardrail_passed": sum(
                    run["negative_guardrail_passed"] for run in negative
                ),
                "negative_guardrail_pass_rate": round(
                    mean(run["negative_guardrail_passed"] for run in negative), 6
                ) if negative else "",
                "avg_turns": round(mean(run["turns"] for run in group), 4),
                "avg_iterations": round(mean(run["iterations"] for run in group), 4),
                "avg_tokens_in": round(mean(run["tokens_in"] for run in group), 4),
                "avg_tokens_out": round(mean(run["tokens_out"] for run in group), 4),
                "all_provider_tokens_measured": all(run["tokens_measured"] for run in group),
                "avg_cost_usd": round(mean(run["cost_usd"] for run in group), 8),
                "prompt_tokens_estimated_chars_div_4_per_call": audit[
                    "estimated_tokens_chars_div_4"
                ],
                "avg_retransmitted_prompt_tokens_estimated": round(
                    mean(
                        audit["estimated_tokens_chars_div_4"] * run["iterations"]
                        for run in group
                    ),
                    4,
                ),
                "avg_tool_return_tokens_estimated_chars_div_4": round(
                    mean(return_tokens), 4
                ) if return_tokens else 0,
            }
        )
    return rows


def _tool_return_summaries(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for run in runs:
        for observation in run["observations"]:
            groups[(run["model"], run["variant"], observation["name"])].append(
                observation["return_tokens_estimated_chars_div_4"]
            )
    return [
        {
            "model": model,
            "variant": variant,
            "tool": tool,
            "calls": len(values),
            "avg_return_tokens_estimated_chars_div_4": round(mean(values), 4),
            "min_return_tokens_estimated_chars_div_4": min(values),
            "max_return_tokens_estimated_chars_div_4": max(values),
        }
        for (model, variant, tool), values in sorted(groups.items())
    ]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("Cannot write an empty result table.")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
