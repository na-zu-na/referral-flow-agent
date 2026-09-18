#!/usr/bin/env python3
"""Run one auditable, resumable D5 live-model battery on the final core set.

Place this file at the root of the 3d842b7 repository snapshot. The script
never reads the answer key while the Agent is running. It uses the repository's
own scorer after saving the raw model traces.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent import run_case
from config import RunConfig
from evaluation.harness import rescore_saved, select_cases, write_results


ROOT = Path(__file__).resolve().parent
HASH_FILES = (
    "agent/loop.py",
    "prompt.py",
    "tools/registry.py",
    "guardrails/__init__.py",
    "evaluation/harness.py",
    "data/evaluation_cases_B.json",
    "data/expected_outcomes_B.json",
    "data/fixtures/referrals.json",
    "data/fixtures/patients.json",
    "data/fixtures/clinic_slots.json",
    "data/fixtures/urgency_bands.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
    """Return auditable actual/estimated charge, never silently count unknown as zero."""
    if record.get("cost_source") == "provider_reported":
        value = record.get("provider_cost_usd")
        return float(value) if isinstance(value, (float, int)) and value >= 0 else None
    if settings.price_input_per_million > 0 and settings.price_output_per_million > 0:
        value = record.get("calculated_cost_usd")
        return float(value) if isinstance(value, (float, int)) and value >= 0 else None
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
    parser.add_argument("--operator", default="ZHOU YU", help="person actually operating this battery")
    parser.add_argument("--source-commit", default="3d842b705afb58610a781b2351ddc27d3d9ccc0b")
    parser.add_argument("--resume", action="store_true", help="continue an existing matching battery")
    parser.add_argument("--max-new-runs", type=int,
                        help="pause after this many newly completed trials; useful for a one-trial smoke check")
    args = parser.parse_args()
    if args.max_cost_usd <= 0:
        parser.error("--max-cost-usd must be positive")
    if args.max_new_runs is not None and args.max_new_runs < 1:
        parser.error("--max-new-runs must be positive")
    if not os.getenv("OPENROUTER_API_KEY"):
        parser.error("OPENROUTER_API_KEY is absent; set it locally, never paste it into chat")

    settings = RunConfig.from_env(
        backend="live", model=args.model, prompt_version=args.prompt_version,
        descriptor_version="v2", call_mode="parallel", autonomy="confirm", temperature=0.0,
    )
    cases = select_cases(tier="core")
    if len(cases) != 40 or sum(bool(case["negative_case"]) for case in cases) != 6:
        parser.error("final D5 core set must have exactly 40 cases, including 6 negative cases")
    plan = [(case["case_id"], trial)
            for case in cases
            for trial in range(1, (3 if case["negative_case"] else 1) + 1)]
    assert len(plan) == 52
    hashes = {name: sha256(ROOT / name) for name in HASH_FILES}
    public_config = settings.public_dict()
    public_config.pop("price_input_per_million", None)
    public_config.pop("price_output_per_million", None)
    identity = {
        "source_commit": args.source_commit,
        "operator": args.operator,
        "model": args.model,
        "prompt_version": args.prompt_version,
        "descriptor_version": "v2",
        "call_mode": "parallel",
        "autonomy": "confirm",
        "temperature": 0.0,
        "case_count": 40,
        "negative_case_count": 6,
        "planned_run_count": len(plan),
        "trial_policy": "one ordinary run; three negative-case runs",
        "source_hashes": hashes,
        "public_config": public_config,
    }

    out = args.out.resolve()
    manifest_path = out / "battery_manifest.json"
    raw_path = out / "raw_checkpoint.jsonl"
    error_path = out / "provider_errors.jsonl"
    if out.exists() and not args.resume:
        parser.error(f"{out} exists; choose a new --out or explicitly --resume")
    if args.resume:
        if not manifest_path.exists():
            parser.error("--resume requires an existing battery_manifest.json")
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing["identity"] != identity:
            parser.error("the existing battery identity or source files differ; cannot resume")
    else:
        out.mkdir(parents=True)
        manifest_path.write_text(json.dumps({
            "identity": identity,
            "started_at_utc": now_utc(),
            "cost_cap_usd": args.max_cost_usd,
            "disclosure": "One operator ran all batteries with instructor approval; results are not attributed to other operators.",
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    saved = read_jsonl(raw_path)
    completed = {(item["case_id"], item["trial"]) for item in saved}
    if len(completed) != len(saved) or not completed.issubset(set(plan)):
        parser.error("checkpoint contains duplicate or out-of-plan trials")
    provider_errors = read_jsonl(error_path)
    prior_costs = [charge(item["record"], settings) for item in saved + provider_errors]
    if any(value is None for value in prior_costs):
        parser.error("saved live charge is unknown; provide A2_PRICE_INPUT and A2_PRICE_OUTPUT to resume")
    spent = sum(prior_costs)
    new_runs = 0

    def approve(event: dict) -> bool:
        return (event.get("type") == "confirmation_required"
                and event.get("call", {}).get("name") == "book_slot")

    try:
        for index, (case_id, trial) in enumerate(plan, 1):
            if (case_id, trial) in completed:
                continue
            if spent >= args.max_cost_usd:
                print(f"Stopped at cost cap: ${spent:.6f} / ${args.max_cost_usd:.2f}", file=sys.stderr)
                break
            record = run_case(case_id, settings, approve=approve)
            item = {"case_id": case_id, "trial": trial, "record": record}
            cost = charge(record, settings)
            if record.get("status") == "backend_error":
                append_jsonl(error_path, item)
                if cost is not None:
                    spent += cost
                print(f"Provider error on {case_id} trial {trial}; stopped, details in {error_path}", file=sys.stderr)
                break
            append_jsonl(raw_path, item)
            completed.add((case_id, trial))
            new_runs += 1
            print(f"[{index}/{len(plan)}] {case_id} trial {trial}: {record['status']}; "
                  f"charge={cost if cost is not None else 'unknown'}", flush=True)
            if cost is None:
                print("Stopped: provider omitted cost and no positive local token prices are set.", file=sys.stderr)
                break
            spent += cost
            if args.max_new_runs is not None and new_runs >= args.max_new_runs:
                print("Paused after requested smoke-check trial; resume with --resume.")
                break
    except KeyboardInterrupt:
        print("Interrupted; saved trials can be resumed with --resume.", file=sys.stderr)
    finally:
        export_scored(raw_path, out)
        (out / "progress.json").write_text(json.dumps({
            "updated_at_utc": now_utc(),
            "completed": len(completed),
            "planned": len(plan),
            "complete": len(completed) == len(plan),
            "charge_usd_recorded": round(spent, 8),
            "cost_cap_usd": args.max_cost_usd,
            "review_status": "not reviewed; see scored_unreviewed/judgement_queue.csv",
        }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
