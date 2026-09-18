#!/usr/bin/env python3
"""Legacy D5 helpers; the CLI now delegates to the frozen final 5+1 builder."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from evaluation.harness import select_cases
from run_d5_battery import EXPECTED_NEGATIVE_RUNS, EXPECTED_RUNS, build_plan, read_jsonl


def _expected_keys() -> set[tuple[str, int]]:
    return set(build_plan(select_cases(tier="core")))


def load_battery(path: Path) -> dict:
    manifest = json.loads((path / "battery_manifest.json").read_text(encoding="utf-8"))
    progress = json.loads((path / "progress.json").read_text(encoding="utf-8"))
    if not progress.get("complete") or progress.get("completed") != EXPECTED_RUNS:
        raise ValueError(f"{path}: battery is incomplete")
    if not (path / "reviewed.csv").exists():
        raise ValueError(f"{path}: reviewed.csv is missing")
    reviewed = path / "scored_reviewed"
    summary = json.loads((reviewed / "summary.json").read_text(encoding="utf-8"))
    with (reviewed / "trials.csv").open(newline="", encoding="utf-8") as stream:
        trials = list(csv.DictReader(stream))
    with (reviewed / "runs.csv").open(newline="", encoding="utf-8") as stream:
        runs = list(csv.DictReader(stream))
    raw = read_jsonl(path / "raw_checkpoint.jsonl")
    identity = manifest["identity"]
    if (
        summary["runs"] != EXPECTED_RUNS
        or summary["cases"] != 40
        or summary["negative_runs"] != EXPECTED_NEGATIVE_RUNS
    ):
        raise ValueError(f"{path}: wrong case/trial denominator")
    if summary["pending_review"] or summary["final_pass_rate"] is None:
        raise ValueError(f"{path}: judgement review is incomplete")
    measured_runs = summary.get("tokens_measured_runs")
    raw_measured_runs = sum(
        item.get("record", {}).get("tokens_measured") is True for item in raw
    )
    if measured_runs != raw_measured_runs:
        raise ValueError(f"{path}: summary and raw token-measurement counts differ")
    if len(trials) != EXPECTED_RUNS or len(runs) != EXPECTED_RUNS or len(raw) != EXPECTED_RUNS:
        raise ValueError(f"{path}: raw and reviewed tables must contain {EXPECTED_RUNS} rows")
    keys = {(row["case_id"], int(row["trial"])) for row in trials}
    run_keys = {(row["case_id"], int(row["trial"])) for row in runs}
    raw_keys = {(item["case_id"], int(item["trial"])) for item in raw}
    expected_keys = _expected_keys()
    if keys != run_keys or keys != raw_keys or keys != expected_keys:
        raise ValueError(f"{path}: raw and reviewed case/trial rows differ from the D5 plan")
    negative = [row for row in trials if row["negative_case"].lower() == "true"]
    negative_counts = Counter(row["case_id"] for row in negative)
    if (
        len(negative) != EXPECTED_NEGATIVE_RUNS
        or set(negative_counts.values()) != {3}
    ):
        raise ValueError(f"{path}: each negative case must have 3 total trials")
    if any(row["backend"] != "live" or row["model"] != identity["model"] for row in runs):
        raise ValueError(f"{path}: non-live or wrong-model run found")
    if any(
        (record := item.get("record", {})).get("case_id") != item["case_id"]
        or (
            record.get("tokens_measured") is not True
            and record.get("status") != "invalid_model_output"
        )
        or record.get("backend") != "live"
        or record.get("model") != identity["model"]
        or record.get("prompt_version") != identity["prompt_version"]
        or record.get("descriptor_version") != "v2"
        or record.get("call_mode") != "parallel"
        or record.get("autonomy") != "confirm"
        or record.get("temperature") != 0.0
        for item in raw
    ):
        raise ValueError(f"{path}: raw trace differs from the frozen live configuration")
    if any(
        row["backend"] != "live"
        or row["model"] != identity["model"]
        or row["prompt_version"] != identity["prompt_version"]
        or row["descriptor_version"] != "v2"
        or row["call_mode"] != "parallel"
        or row["autonomy"] != "confirm"
        for row in trials
    ):
        raise ValueError(f"{path}: trial differs from the frozen battery configuration")
    return {
        "path": path,
        "identity": identity,
        "progress": progress,
        "summary": summary,
        "trials": trials,
        "runs": runs,
        "keys": keys,
        "measured_runs": measured_runs,
    }


def validate_battery_set(batteries: list[dict]) -> tuple[list[dict], dict]:
    v2 = [item for item in batteries if item["identity"]["prompt_version"] == "v2"]
    v1 = [item for item in batteries if item["identity"]["prompt_version"] == "v1"]
    if len(v2) != 5:
        raise ValueError("the team design requires exactly five distinct V2 live models")
    model_ids = [item["identity"]["model"] for item in v2]
    if len(model_ids) != len(set(model_ids)):
        raise ValueError("V2 model IDs are not distinct")
    if len(v1) != 1 or v1[0]["identity"]["model"] not in model_ids:
        raise ValueError("one V2 model must also have exactly one V1 battery")
    operators = [item["identity"].get("operator") for item in v2 + v1]
    if None in operators or len(set(operators)) != len(operators):
        raise ValueError("each team member must operate exactly one battery")
    baseline = v2[0]
    for item in v2[1:]:
        fields = [
            "source_commit", "descriptor_version", "call_mode", "autonomy",
            "temperature", "planned_run_count", "public_config",
        ]
        fields.append("source_hashes" if "source_hashes" in baseline["identity"] else "negative_run_count")
        for field in fields:
            left, right = baseline["identity"][field], item["identity"][field]
            if field == "public_config":
                left, right = dict(left), dict(right)
                left.pop("model", None)
                right.pop("model", None)
            if left != right:
                raise ValueError(f"V2 battery mismatch in {field}: {item['path']}")
        if item["keys"] != baseline["keys"]:
            raise ValueError(f"V2 battery has different case/trial keys: {item['path']}")
    old = v1[0]
    same_model_v2 = next(item for item in v2 if item["identity"]["model"] == old["identity"]["model"])
    if old["identity"]["source_commit"] != baseline["identity"]["source_commit"]:
        raise ValueError("V1 and V2 use different source commits")
    if "source_hashes" in baseline["identity"] and (
        old["identity"].get("source_hashes") != baseline["identity"]["source_hashes"]
    ):
        raise ValueError("V1 and V2 use different source files")
    if old["keys"] != baseline["keys"]:
        raise ValueError("V1 and V2 use different case/trial keys")
    old_config = dict(old["identity"]["public_config"])
    new_config = dict(same_model_v2["identity"]["public_config"])
    old_config.pop("prompt_version", None)
    new_config.pop("prompt_version", None)
    if old_config != new_config:
        raise ValueError("V1 and V2 differ in more than prompt version")
    if "local_token_prices_usd_per_million" in old["identity"] and (
        old["identity"]["local_token_prices_usd_per_million"]
        != same_model_v2["identity"]["local_token_prices_usd_per_million"]
    ):
        raise ValueError("V1 and V2 use different local token prices")
    return v2, same_model_v2


def ratio(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator} ({100 * numerator / denominator:.1f}%)"


def pass_counts(item: dict) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in item["trials"]:
        counts[row["case_id"]] += row["passed"] == "True"
    return dict(counts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--battery", action="append", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    batteries = [load_battery(path) for path in args.battery]
    v2, same_model_v2 = validate_battery_set(batteries)
    old = next(item for item in batteries if item["identity"]["prompt_version"] == "v1")
    source_commit = v2[0]["identity"]["source_commit"]

    lines = [
        "# D5 live-model comparison",
        "",
        f"Source commit: `{source_commit}`. Each model uses 40 cases and {EXPECTED_RUNS} trials.",
        "This 40-case/6-negative configuration exceeds the 30-case/6-negative passing floor; "
        "it does not claim the recommended 40-case/8-negative shape.",
        "",
        "| Model | Operator | Final pass | Negative pass | Unsafe booking attempts | "
        "Usage measured | Tokens in/out | Cost USD | Cost source | Mean turns |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for item in v2:
        summary = item["summary"]
        runs = item["runs"]
        tokens_in = sum(int(row["tokens_in"] or 0) for row in runs)
        tokens_out = sum(int(row["tokens_out"] or 0) for row in runs)
        cost_sources = ", ".join(sorted({row["cost_source"] or "unknown" for row in runs}))
        lines.append(
            f"| `{item['identity']['model']}` | {item['identity']['operator']} | "
            f"{ratio(summary['final_pass'], EXPECTED_RUNS)} | "
            f"{ratio(summary['negative_final_pass'], EXPECTED_NEGATIVE_RUNS)} | "
            f"{summary['negative_booking_attempts']} | "
            f"{item['measured_runs']}/{EXPECTED_RUNS} | {tokens_in:,}/{tokens_out:,} | "
            f"{item['progress']['charge_usd_recorded']:.6f} | {cost_sources} | "
            f"{summary['mean_turns']:.2f} |"
        )

    counts = {item["identity"]["model"]: pass_counts(item) for item in v2}
    case_ids = sorted(next(iter(counts.values())))
    lines += ["", "## Case-level divergences", ""]
    divergent = 0
    for case_id in case_ids:
        values = {model: observed[case_id] for model, observed in counts.items()}
        if len(set(values.values())) > 1:
            divergent += 1
            lines.append(f"- `{case_id}`: " + "; ".join(
                f"`{model}` {passed}" for model, passed in sorted(values.items())
            ))
    if not divergent:
        lines.append("- No case differed in final pass count across the five V2 models.")

    lines += ["", "## Failure categories", ""]
    for item in v2:
        categories = item["summary"].get("automatic_failure_categories") or {}
        lines.append(f"- `{item['identity']['model']}`: " + (
            ", ".join(f"{name}={count}" for name, count in sorted(categories.items()))
            if categories else "none"
        ))

    lines += ["", "## Same-model V1/V2 prompt comparison", ""]
    lines.append(
        f"Comparison owner: {old['identity']['operator']}. The V1 battery was operated by "
        f"{old['identity']['operator']}; the matching V2 reference battery was operated by "
        f"{same_model_v2['identity']['operator']}."
    )
    lines.append("")
    lines.append(
        f"`{old['identity']['model']}`: V1 {ratio(old['summary']['final_pass'], EXPECTED_RUNS)}; "
        f"V2 {ratio(same_model_v2['summary']['final_pass'], EXPECTED_RUNS)}. "
        f"V1 cost ${old['progress']['charge_usd_recorded']:.6f}; "
        f"V2 cost ${same_model_v2['progress']['charge_usd_recorded']:.6f}."
    )
    lines += [
        "",
        "Interpret the measured failure cases, price tiers, and whether the more expensive "
        "models justify their cost in the final report.",
        "",
    ]
    incomplete_usage = [
        f"`{item['identity']['model']}` {item['measured_runs']}/{EXPECTED_RUNS}"
        for item in v2 + [old]
        if item["measured_runs"] != EXPECTED_RUNS
    ]
    lines += [
        "## Evidence limitations",
        "",
        "- The six batteries contain 312 formal runs; no additional live calls are needed "
        "for the declared 40-case/6-negative passing-floor configuration.",
        "- Incomplete provider usage: " + (
            "; ".join(incomplete_usage) if incomplete_usage else "none"
        ) + ".",
        "- Account-level billing is reconciled separately in `D5_COST_RECONCILIATION.md`.",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(args.out.resolve())


if __name__ == "__main__":
    from D5.final_5plus1 import main as final_main

    final_main()
