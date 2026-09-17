#!/usr/bin/env python3
"""Run the Problem B evaluation set and save auditable trial results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.harness import evaluate, load_reviews, rescore_saved, write_results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=["core", "extended", "all"], default="core")
    parser.add_argument("--case", action="append", dest="case_ids", metavar="REF-ID")
    parser.add_argument("--trials", type=int, help="override manifest trial count")
    parser.add_argument("--backend", choices=["scripted", "live"], default="scripted")
    parser.add_argument("--model", help="required for live backend")
    parser.add_argument("--prompt-version", choices=["v1", "v2"], default="v2")
    parser.add_argument("--descriptors", choices=["v1", "v2"], default="v2")
    parser.add_argument("--call-mode", choices=["parallel", "sequential"], default="parallel")
    parser.add_argument("--autonomy", choices=["suggest", "confirm", "act"], default="confirm")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--approve-simulated-booking", action="store_true",
                        help="trusted local callback for simulated live confirm runs")
    parser.add_argument("--reviews", type=Path,
                        help="completed claim-level judgement CSV from an earlier run")
    parser.add_argument("--rescore", type=Path, metavar="TRIALS.JSONL",
                        help="rescore saved records without rerunning the Agent or model")
    parser.add_argument("--out", type=Path, default=Path("results/evaluation"))
    args = parser.parse_args()
    if args.rescore:
        if args.out.resolve() == args.rescore.parent.resolve():
            parser.error("--out must differ from the saved run directory when rescoring")
        results = rescore_saved(args.rescore, reviews=load_reviews(args.reviews))
        write_results(results, args.out)
        summary = json.loads((args.out / "summary.json").read_text(encoding="utf-8"))
        print(json.dumps(summary, indent=2))
        print(f"Rescored results saved in {args.out.resolve()}")
        return
    if args.backend == "live" and not args.model:
        parser.error("--model is required for live runs")
    if args.approve_simulated_booking and (args.backend != "live" or args.autonomy != "confirm"):
        parser.error("--approve-simulated-booking applies to live confirm runs only")

    try:
        from agent import run_case
        from config import RunConfig
    except ImportError as exc:
        parser.error(
            "the Agent controller is not integrated in this checkout yet; "
            "run this scorer with the complete Member 1 package"
        )
        raise AssertionError from exc

    config = RunConfig.from_env(
        backend=args.backend,
        model=args.model,
        prompt_version=args.prompt_version,
        descriptor_version=args.descriptors,
        call_mode=args.call_mode,
        autonomy=args.autonomy,
        temperature=args.temperature,
    )

    def approve(event: dict) -> bool:
        return (
            args.approve_simulated_booking
            and event.get("type") == "confirmation_required"
            and event.get("call", {}).get("name") == "book_slot"
        )

    def runner(case_id: str) -> dict:
        return run_case(case_id, config, approve=approve if args.approve_simulated_booking else None)

    results = evaluate(
        runner,
        tier=args.tier,
        case_ids=set(args.case_ids) if args.case_ids else None,
        trials_override=args.trials,
        reviews=load_reviews(args.reviews),
    )
    write_results(results, args.out)
    summary = json.loads((args.out / "summary.json").read_text(encoding="utf-8"))
    print(json.dumps(summary, indent=2))
    print(f"Results saved in {args.out.resolve()}")


if __name__ == "__main__":
    main()
