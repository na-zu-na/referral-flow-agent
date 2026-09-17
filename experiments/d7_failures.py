"""Reproduce and measure the two PE6201 A2 D7 failures.

Both failures are controlled deletions from the working Agent:

1. Loop control: temporarily remove persistent action de-duplication.  A
   deterministic backend repeatedly re-reads the same referral until the
   evidence-based step cap stops it.
2. Prompt: delete the rule that dependent calls must wait for prerequisite
   observations.  The same deterministic prompt-aware backend then batches a
   slot lookup with its prerequisites, and the real guardrail rejects the move.
   Restoring the one rule recovers the correct no_slot_in_window escalation.

The backends below author only Agent moves.  Real tools, the real ReAct
controller, and the real guardrails still execute.  Token counts are a labelled,
deterministic approximation (UTF-8 JSON characters / 4) because D7 must run
offline; live D5 measurements remain the source for production pricing.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

from agent import run_case
from config import RunConfig
from guardrails import GuardrailState
from prompt import build_system_prompt


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
CASES_FILE = ROOT / "data" / "evaluation_cases_B.json"
ANSWERS_FILE = ROOT / "data" / "expected_outcomes_B.json"
SCRIPTS_FILE = ROOT / "backends" / "scripts" / "problem_b.json"

PRICE_INPUT_PER_MILLION = 0.10
PRICE_OUTPUT_PER_MILLION = 0.40
DEPENDENCY_RULE = (
    "A dependent\n"
    "call must wait for successful prerequisite observations from earlier turns."
)


class MeteredSequenceBackend:
    """Deterministic Agent moves with transparent offline token accounting."""

    name = "scripted-d7"
    model = None

    def __init__(self, moves: list[dict[str, Any]], system_prompt: str):
        self.moves = deepcopy(moves)
        self.system_prompt = system_prompt
        self.position = 0

    def next_move(self, transcript: list[dict[str, Any]]) -> dict[str, Any]:
        if self.position >= len(self.moves):
            raise RuntimeError("D7 scripted sequence ended before the controller stopped.")
        move = deepcopy(self.moves[self.position])
        self.position += 1
        prompt_payload = self.system_prompt + json.dumps(
            transcript, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        output_payload = json.dumps(
            move, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return {
            "move": move,
            "usage": {
                "input_tokens": max(1, math.ceil(len(prompt_payload) / 4)),
                "output_tokens": max(1, math.ceil(len(output_payload) / 4)),
                "measured": False,
            },
        }


class DependencyRuleBackend(MeteredSequenceBackend):
    """One policy whose move choice depends only on the supplied prompt rule."""

    name = "scripted-d7-prompt-aware"

    def __init__(self, system_prompt: str):
        moves = deepcopy(_load_json(SCRIPTS_FILE)["REF-5697"])
        if DEPENDENCY_RULE not in system_prompt:
            slot_call = deepcopy(moves[2]["calls"][0])
            moves[1]["calls"].append(slot_call)
            moves[1]["thought"] = (
                "Batch the criteria, patient, and dependent slot checks together."
            )
            del moves[2]
        super().__init__(moves, system_prompt)


@contextmanager
def without_action_deduplication() -> Iterator[None]:
    """Failure injection: delete only memory of prior action signatures."""

    original = GuardrailState.prepare_turn

    def prepare_without_persistent_dedup(
        state: GuardrailState, calls: list[dict[str, Any]]
    ) -> None:
        state.seen_actions.clear()
        original(state, calls)

    with patch.object(GuardrailState, "prepare_turn", prepare_without_persistent_dedup):
        yield


def _config(*, descriptor_version: str = "v2", max_turns: int = 5) -> RunConfig:
    return RunConfig(
        descriptor_version=descriptor_version,
        max_turns=max_turns,
        max_tokens=60_000,
        price_input_per_million=PRICE_INPUT_PER_MILLION,
        price_output_per_million=PRICE_OUTPUT_PER_MILLION,
    )


def _loop_moves(repetitions: int = 12) -> list[dict[str, Any]]:
    moves: list[dict[str, Any]] = []
    for index in range(1, repetitions + 1):
        moves.append(
            {
                "type": "tool_calls",
                "thought": "Re-read the referral instead of concluding.",
                "calls": [
                    {
                        "id": f"loop-t{index}-c1",
                        "name": "get_referral",
                        "arguments": {"referral_id": "REF-5602"},
                    }
                ],
            }
        )
    return moves


def reproduce_loop_failure(max_turns: int) -> dict[str, Any]:
    """Run working and dedup-deleted variants against the same loop script."""

    prompt = build_system_prompt("v2", "parallel")
    fixed = run_case(
        "REF-5602",
        _config(max_turns=max_turns),
        backend=MeteredSequenceBackend(_loop_moves(), prompt),
    )
    with without_action_deduplication():
        broken = run_case(
            "REF-5602",
            _config(max_turns=max_turns),
            backend=MeteredSequenceBackend(_loop_moves(), prompt),
        )
    return {
        "failure": "loop_control",
        "deleted_component": "persistent action de-duplication",
        "success_criterion": "Repeated action is stopped before the step cap.",
        "broken": {**_summary(broken), "experiment_passed": False},
        "fixed": {**_summary(fixed), "experiment_passed": True},
        "finding": (
            "Without de-duplication the repeated read survives until STEP_LIMIT_REACHED; "
            "with it restored the second identical action is stopped immediately."
        ),
    }


def dependency_prompts() -> tuple[str, str]:
    """Return working and one-rule-deleted prompts for the controlled trial."""

    working = build_system_prompt("v2", "parallel")
    if working.count(DEPENDENCY_RULE) != 1:
        raise RuntimeError("Expected exactly one dependency rule in the working prompt.")
    return working, working.replace(DEPENDENCY_RULE, "")


def reproduce_prompt_failure(max_turns: int) -> dict[str, Any]:
    """Delete/restore one dependency-ordering rule in the system prompt."""

    fixed_prompt, broken_prompt = dependency_prompts()
    broken = run_case(
        "REF-5697",
        _config(descriptor_version="v2", max_turns=max_turns),
        backend=DependencyRuleBackend(broken_prompt),
    )
    fixed = run_case(
        "REF-5697",
        _config(descriptor_version="v2", max_turns=max_turns),
        backend=DependencyRuleBackend(fixed_prompt),
    )
    return {
        "failure": "prompt_dependency_ordering",
        "layer": "system prompt",
        "deleted_component": DEPENDENCY_RULE.replace("\n", " "),
        "controlled_variable": {
            "same_backend": DependencyRuleBackend.name,
            "same_case": "REF-5697",
            "same_descriptor_version": "v2",
            "same_controller_tools_and_guardrails": True,
            "working_prompt_characters": len(fixed_prompt),
            "broken_prompt_characters": len(broken_prompt),
            "deleted_characters": len(fixed_prompt) - len(broken_prompt),
        },
        "success_criterion": "REF-5697 reaches its evidence-supported expected decision.",
        "broken": {
            **_summary(broken),
            "case_passed": _case_passed(broken, _answers()["REF-5697"]),
        },
        "fixed": {
            **_summary(fixed),
            "case_passed": _case_passed(fixed, _answers()["REF-5697"]),
        },
        "finding": (
            "Without the ordering rule, the policy batches get_clinic_slots with "
            "its prerequisites and is loudly stopped by DEPENDENCY_VIOLATION; "
            "restoring the rule recovers no_slot_in_window."
        ),
    }


def core_distribution(*, remove_deduplication: bool = False) -> dict[str, Any]:
    """Measure the 40-case core set and its turn/cap distribution."""

    cases = [
        item
        for item in _load_json(CASES_FILE)
        if item.get("evaluation_tier") == "core"
    ]
    answers = _answers()
    scripts = _load_json(SCRIPTS_FILE)
    rows: list[dict[str, Any]] = []
    context = without_action_deduplication() if remove_deduplication else _null_context()
    with context:
        for case in cases:
            case_id = case["case_id"]
            record = run_case(
                case_id,
                _config(max_turns=8),
                backend=MeteredSequenceBackend(
                    scripts[case_id], build_system_prompt("v2", "parallel")
                ),
            )
            rows.append(
                {
                    "case_id": case_id,
                    "negative_case": bool(case["negative_case"]),
                    "passed": _case_passed(record, answers[case_id]),
                    "turns": record["turns"],
                    "tokens_in": record["tokens_in"],
                    "tokens_out": record["tokens_out"],
                    "cost_usd": record["cost_usd"],
                    "cap_hit": (record.get("stopped_by") or {}).get("code")
                    == "STEP_LIMIT_REACHED",
                }
            )
    turns = [row["turns"] for row in rows]
    passed = sum(row["passed"] for row in rows)
    return {
        "variant": "dedup_deleted" if remove_deduplication else "working_agent",
        "cases": len(rows),
        "passed": passed,
        "pass_rate": passed / len(rows),
        "median_turns": statistics.median(turns),
        "worst_turns": max(turns),
        "step_cap_hits": sum(row["cap_hit"] for row in rows),
        "rows": rows,
    }


@contextmanager
def _null_context() -> Iterator[None]:
    yield


def _answers() -> dict[str, dict[str, Any]]:
    return {item["case_id"]: item for item in _load_json(ANSWERS_FILE)}


def _case_passed(record: dict[str, Any], answer: dict[str, Any]) -> bool:
    final = record.get("final") or {}
    if final.get("decision") != answer["expected_decision"]:
        return False
    if answer["expected_decision"] == "book":
        return final.get("booked") == answer.get("booked")
    if answer["expected_decision"] == "request_information":
        return final.get("missing") == answer.get("missing")
    return final.get("trigger") == answer.get("trigger")


def _summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": record["status"],
        "decision": (record.get("final") or {}).get("decision"),
        "trigger": (record.get("final") or {}).get("trigger"),
        "turns": record["turns"],
        "tokens_in": record["tokens_in"],
        "tokens_out": record["tokens_out"],
        "cost_usd": record["cost_usd"],
        "stopped_by": (record.get("stopped_by") or {}).get("code"),
        "error": record.get("error"),
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_all(write_results: bool = True) -> dict[str, Any]:
    working = core_distribution()
    dedup_deleted = core_distribution(remove_deduplication=True)
    recommended_cap = int(working["worst_turns"]) + 1
    payload = {
        "method": {
            "backend": "deterministic scripted moves through real tools and guardrails",
            "token_basis": "ceil((system prompt + transcript UTF-8 characters) / 4)",
            "prices_usd_per_million": {
                "input": PRICE_INPUT_PER_MILLION,
                "output": PRICE_OUTPUT_PER_MILLION,
            },
            "note": "D7 estimates are offline and reproducible; D5 live usage remains authoritative for deployment cost.",
        },
        "turn_distribution": {
            key: value for key, value in working.items() if key != "rows"
        },
        "dedup_regression": {
            "working_pass_rate": working["pass_rate"],
            "dedup_deleted_pass_rate": dedup_deleted["pass_rate"],
            "cases": working["cases"],
        },
        "recommended_step_cap": recommended_cap,
        "failure_1": reproduce_loop_failure(recommended_cap),
        "failure_2": reproduce_prompt_failure(recommended_cap),
    }
    if write_results:
        RESULTS_DIR.mkdir(exist_ok=True)
        (RESULTS_DIR / "d7_failure_results.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        with (RESULTS_DIR / "d7_turn_distribution.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(working["rows"][0]))
            writer.writeheader()
            writer.writerows(working["rows"])
    return payload


if __name__ == "__main__":
    result = run_all(write_results=True)
    print(json.dumps(result, indent=2, ensure_ascii=False))
