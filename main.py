#!/usr/bin/env python3
"""Simple entry point for one complete Member 1 Agent run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent import run_case
from config import RunConfig
from prompt import prompt_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Problem B referral Agent.")
    parser.add_argument("case_id", nargs="?", default="REF-5602")
    parser.add_argument("--backend", choices=("scripted", "live"))
    parser.add_argument("--model")
    parser.add_argument("--prompt-version", choices=("v1", "v2"))
    parser.add_argument("--descriptors", choices=("v1", "v2"))
    parser.add_argument("--call-mode", choices=("sequential", "parallel"))
    parser.add_argument("--autonomy", choices=("suggest", "confirm", "act"))
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--show-prompt", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    overrides = {
        name: value
        for name, value in {
            "backend": args.backend,
            "model": args.model,
            "prompt_version": args.prompt_version,
            "descriptor_version": args.descriptors,
            "call_mode": args.call_mode,
            "autonomy": args.autonomy,
        }.items()
        if value is not None
    }
    config = RunConfig.from_env(**overrides)
    if args.show_prompt:
        print(
            json.dumps(
                prompt_audit(
                    config.descriptor_version,
                    config.call_mode,
                    config.prompt_version,
                ),
                indent=2,
            )
        )
        return 0
    print(config.summary())
    record = run_case(args.case_id, config, verbose=args.verbose)
    rendered = json.dumps(record, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if record["status"] in {"completed", "guardrail_stopped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
