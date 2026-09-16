"""Trace helpers used by the Agent, evaluation, cost, and failure analysis."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RunTrace:
    transcript: list[dict[str, Any]] = field(default_factory=list)
    moves: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)

    def add_move(self, move: dict[str, Any]) -> None:
        self.moves.append(deepcopy(move))

    def add_call(self, turn: int, call: dict[str, Any]) -> None:
        self.tool_calls.append({"turn": turn, **deepcopy(call)})

    def add_observation(self, turn: int, call: dict[str, Any], result: dict[str, Any]) -> None:
        compact = json.dumps(result, sort_keys=True, separators=(",", ":"))
        self.observations.append(
            {
                "turn": turn,
                "call_id": call["id"],
                "name": call["name"],
                "result": deepcopy(result),
                "return_characters": len(compact),
                "return_tokens_estimated_chars_div_4": (len(compact) + 3) // 4,
            }
        )

    def append_model_move(self, move: dict[str, Any]) -> None:
        self.transcript.append({"role": "assistant", "content": deepcopy(move)})

    def append_observations(self, observations: list[dict[str, Any]]) -> None:
        self.transcript.append(
            {
                "role": "user",
                "content": {
                    "type": "tool_observations",
                    "observations": deepcopy(observations),
                },
            }
        )
