#!/usr/bin/env python3
"""Run one paid live Prompt/descriptor trial with trusted CLI confirmation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from agent import run_case
from config import RunConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", default="REF-5602")
    parser.add_argument("--prompt-version", choices=("v1", "v2"), required=True)
    parser.add_argument("--descriptors", choices=("v1", "v2"), required=True)
    parser.add_argument("--model", required=True, help="OpenRouter model ID")
    parser.add_argument("--call-mode", choices=("sequential", "parallel"), default="parallel")
    parser.add_argument("--trial", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    return parser


def approve_booking(event: dict) -> bool:
    print("\nTrusted confirmation requested for this simulated booking:")
    print(json.dumps(event["call"], ensure_ascii=False, indent=2))
    return input("Approve? Type y: ").strip().lower() == "y"


def main() -> int:
    args = build_parser().parse_args()
    if args.trial < 1:
        raise SystemExit("--trial must be a positive integer.")
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("Set OPENROUTER_API_KEY before a live run.")

    config = RunConfig(
        backend="live",
        model=args.model,
        api_key=api_key,
        prompt_version=args.prompt_version,
        descriptor_version=args.descriptors,
        call_mode=args.call_mode,
        autonomy="confirm",
        temperature=0.0,
    )
    record = run_case(
        args.case_id,
        config,
        approve=approve_booking,
        verbose=True,
    )
    payload = {"config": config.public_dict(), "trial": args.trial, "record": record}
    filename = (
        f"prompt_{args.prompt_version}_descriptors_{args.descriptors}_"
        f"{args.model.replace('/', '_')}_{args.case_id}_trial{args.trial}.json"
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / filename
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\nStatus:", record["status"])
    print("Final:", json.dumps(record["final"], ensure_ascii=False, indent=2))
    print("Turns:", record["turns"])
    print("Tokens:", record["tokens_in"], "in /", record["tokens_out"], "out")
    print("Tokens measured:", record["tokens_measured"])
    print("Error:", record["error"])
    print("Result:", output.resolve())
    return 0 if record["status"] in {"completed", "guardrail_stopped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
