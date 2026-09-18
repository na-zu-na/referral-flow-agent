#!/usr/bin/env python3
"""Run one auditable and resumable OpenRouter D5 battery."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent import run_case
from config import RunConfig
from evaluation.harness import rescore_saved, select_cases, write_results


ROOT = Path(__file__).resolve().parent
EXPECTED_CASES = 40
EXPECTED_NEGATIVE_CASES = 6
EXPECTED_RUNS = 52
EXPECTED_NEGATIVE_RUNS = 18


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def repository_commit(root: Path = ROOT) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("D5 must run from a committed Git repository") from exc


def tracked_tree_is_clean(root: Path = ROOT) -> bool:
    try:
        return subprocess.run(
            ["git", "diff-index", "--quiet", "HEAD", "--"],
            cwd=root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError as exc:
        raise ValueError("Git is required to freeze the D5 source version") from exc


def runner_is_tracked(root: Path = ROOT) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", "run_d5_battery.py"],
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def build_plan(cases: list[dict]) -> list[tuple[str, int]]:
    negatives = [case for case in cases if case["negative_case"]]
    if len(cases) != EXPECTED_CASES or len(negatives) != EXPECTED_NEGATIVE_CASES:
        raise ValueError("D5 requires the final 40-case core set with 6 negative cases")
    plan = [(case["case_id"], 1) for case in cases]
    plan += [(case["case_id"], trial) for case in negatives for trial in range(2, 4)]
    if len(plan) != EXPECTED_RUNS or len(set(plan)) != EXPECTED_RUNS:
        raise AssertionError("D5 plan must contain 52 unique case/trial pairs")
    return plan


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def append_jsonl(path: Path, item: dict) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(item, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def charge(record: dict, settings: RunConfig) -> float | None:
    """Use provider cost when present, otherwise calculate from measured tokens."""
    if record.get("cost_source") == "provider_reported":
        value = record.get("provider_cost_usd")
        return float(value) if isinstance(value, (float, int)) and value >= 0 else None
    if record.get("tokens_measured") is True and (
        settings.price_input_per_million > 0 or settings.price_output_per_million > 0
    ):
        tokens_in = record.get("tokens_in")
        tokens_out = record.get("tokens_out")
        if all(isinstance(value, int) and value >= 0 for value in (tokens_in, tokens_out)):
            return (
                tokens_in * settings.price_input_per_million
                + tokens_out * settings.price_output_per_million
            ) / 1_000_000
    return None


def export_scored(raw_path: Path, out_dir: Path) -> None:
    if raw_path.exists() and raw_path.stat().st_size:
        write_results(rescore_saved(raw_path), out_dir / "scored_unreviewed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="exact OpenRouter model ID")
    parser.add_argument("--prompt-version", choices=("v1", "v2"), default="v2")
    parser.add_argument("--out", required=True, type=Path, help="new or resumable output directory")
    parser.add_argument("--max-cost-usd", required=True, type=float, help="cap for this battery")
    parser.add_argument("--operator", required=True, help="person actually operating this battery")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.max_cost_usd <= 0:
        parser.error("--max-cost-usd must be positive")
    if not os.getenv("OPENROUTER_API_KEY"):
        parser.error("OPENROUTER_API_KEY is absent; set it locally and never commit it")
    try:
        source_commit = repository_commit()
        if not runner_is_tracked() or not tracked_tree_is_clean():
            parser.error("D5 runner is uncommitted or tracked files differ from HEAD")
        cases = select_cases(tier="core")
        plan = build_plan(cases)
    except ValueError as exc:
        parser.error(str(exc))

    settings = RunConfig.from_env(
        backend="live",
        model=args.model,
        prompt_version=args.prompt_version,
        descriptor_version="v2",
        call_mode="parallel",
        autonomy="confirm",
        temperature=0.0,
    )
    public_config = settings.public_dict()
    public_config.pop("price_input_per_million", None)
    public_config.pop("price_output_per_million", None)
    identity = {
        "source_commit": source_commit,
        "operator": args.operator,
        "model": args.model,
        "prompt_version": args.prompt_version,
        "descriptor_version": "v2",
        "call_mode": "parallel",
        "autonomy": "confirm",
        "temperature": 0.0,
        "case_count": EXPECTED_CASES,
        "negative_case_count": EXPECTED_NEGATIVE_CASES,
        "planned_run_count": EXPECTED_RUNS,
        "negative_run_count": EXPECTED_NEGATIVE_RUNS,
        "trial_policy": "all cases once; two additional trials per negative case",
        "local_token_prices_usd_per_million": {
            "input": settings.price_input_per_million,
            "output": settings.price_output_per_million,
        },
        "public_config": public_config,
    }

    out = args.out.resolve()
    manifest_path = out / "battery_manifest.json"
    raw_path = out / "raw_checkpoint.jsonl"
    error_path = out / "provider_errors.jsonl"
    if out.exists() and not args.resume:
        parser.error(f"{out} exists; choose a new --out or pass --resume")
    if args.resume:
        if not manifest_path.exists():
            parser.error("--resume requires battery_manifest.json")
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("identity") != identity:
            parser.error("battery identity differs; refusing to mix evidence")
    else:
        out.mkdir(parents=True)
        manifest_path.write_text(json.dumps({
            "identity": identity,
            "started_at_utc": now_utc(),
            "initial_cost_cap_usd": args.max_cost_usd,
            "disclosure": "Operator records who actually executed this battery.",
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    saved = read_jsonl(raw_path)
    completed = {(item["case_id"], item["trial"]) for item in saved}
    if len(completed) != len(saved) or not completed.issubset(set(plan)):
        parser.error("checkpoint contains duplicate or out-of-plan trials")
    prior = saved + read_jsonl(error_path)
    prior_costs = [charge(item["record"], settings) for item in prior]
    if any(value is None for value in prior_costs):
        parser.error("saved charge is unknown; set A2_PRICE_INPUT and A2_PRICE_OUTPUT")
    spent = sum(prior_costs)

    def approve(event: dict) -> bool:
        return (
            event.get("type") == "confirmation_required"
            and event.get("call", {}).get("name") == "book_slot"
        )

    try:
        for index, (case_id, trial) in enumerate(plan, 1):
            if (case_id, trial) in completed:
                continue
            if spent >= args.max_cost_usd:
                print(f"Stopped at cost cap: ${spent:.6f}", file=sys.stderr)
                break
            record = run_case(case_id, settings, approve=approve)
            item = {"case_id": case_id, "trial": trial, "record": record}
            cost = charge(record, settings)
            if record.get("status") == "backend_error":
                append_jsonl(error_path, item)
                if cost is not None:
                    spent += cost
                print(f"Provider error on {case_id} trial {trial}; stopped", file=sys.stderr)
                break
            if record.get("tokens_measured") is not True:
                item["evidence_error"] = "provider did not return measured token usage"
                append_jsonl(error_path, item)
                if cost is not None:
                    spent += cost
                print(
                    f"Missing measured token usage on {case_id} trial {trial}; stopped",
                    file=sys.stderr,
                )
                break
            if cost is None:
                item["evidence_error"] = "cost unavailable; configure local token prices"
                append_jsonl(error_path, item)
                print(
                    "Stopped: provider omitted cost and local prices are unset",
                    file=sys.stderr,
                )
                break
            append_jsonl(raw_path, item)
            completed.add((case_id, trial))
            print(
                f"[{index}/{EXPECTED_RUNS}] {case_id} trial {trial}: "
                f"{record['status']}; charge={cost if cost is not None else 'unknown'}",
                flush=True,
            )
            spent += cost
    except KeyboardInterrupt:
        print("Interrupted; resume with --resume", file=sys.stderr)
    finally:
        export_scored(raw_path, out)
        (out / "progress.json").write_text(json.dumps({
            "updated_at_utc": now_utc(),
            "completed": len(completed),
            "planned": EXPECTED_RUNS,
            "complete": len(completed) == EXPECTED_RUNS,
            "charge_usd_recorded": round(spent, 8),
            "current_cost_cap_usd": args.max_cost_usd,
            "review_status": "not reviewed; see scored_unreviewed/judgement_queue.csv",
        }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
