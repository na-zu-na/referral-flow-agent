"""Free, deterministic replay backend for reproducibility and guardrail tests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from agent.schemas import BackendError, validate_move

_SCRIPT_FILE = Path(__file__).resolve().parent / "scripts" / "problem_b.json"


class ScriptedBackend:
    """Replay authored Agent moves while real tools and guardrails still run."""

    name = "scripted"
    model = None

    def __init__(
        self,
        case_id: str,
        script_file: Path | None = None,
        call_mode: str = "parallel",
    ):
        path = script_file or _SCRIPT_FILE
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BackendError(f"Could not load scripted moves from {path}.") from exc
        steps = payload.get(case_id) if isinstance(payload, dict) else None
        if not isinstance(steps, list) or not steps:
            raise BackendError(f"No scripted run exists for case {case_id!r}.")
        if call_mode not in {"sequential", "parallel"}:
            raise ValueError("call_mode must be 'sequential' or 'parallel'.")
        self.case_id = case_id
        validated = [validate_move(step) for step in steps]
        self.steps = _sequentialise(validated) if call_mode == "sequential" else validated
        self.position = 0

    def next_move(self, transcript: list[dict[str, Any]]) -> dict[str, Any]:
        del transcript
        if self.position >= len(self.steps):
            raise BackendError(f"Script for {self.case_id} ended before a final move.")
        move = deepcopy(self.steps[self.position])
        self.position += 1
        return {
            "move": move,
            "usage": {"input_tokens": 0, "output_tokens": 0, "measured": False},
        }


def _sequentialise(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Split independent batches for a controlled D2(c) comparison."""
    output: list[dict[str, Any]] = []
    for step in steps:
        if step["type"] != "tool_calls" or len(step["calls"]) == 1:
            output.append(step)
            continue
        for index, call in enumerate(step["calls"], start=1):
            output.append(
                {
                    "type": "tool_calls",
                    "thought": (
                        f"Sequential comparison step {index}/{len(step['calls'])}: "
                        + step.get("thought", "Execute the next independent check.")
                    ),
                    "calls": [deepcopy(call)],
                }
            )
    return output
