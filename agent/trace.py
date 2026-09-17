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
        self.tool_calls.append(
            {
                "turn": turn,
                **deepcopy(call),
                "observation_tokens": None,
                "observation_chars": None,
                "latency_ms": None,
                "ok": None,
                "error_code": None,
            }
        )

    def add_observation(
        self,
        turn: int,
        call: dict[str, Any],
        result: dict[str, Any],
        latency_ms: float,
    ) -> None:
        compact = json.dumps(result, sort_keys=True, separators=(",", ":"))
        observation_chars = len(compact)
        observation_tokens = (observation_chars + 3) // 4
        error = result.get("error")
        error_code = error.get("code") if isinstance(error, dict) else None
        self.finish_call(
            call,
            observation_tokens=observation_tokens,
            observation_chars=observation_chars,
            latency_ms=latency_ms,
            ok=result.get("ok"),
            error_code=error_code,
        )
        self.observations.append(
            {
                "turn": turn,
                "call_id": call["id"],
                "name": call["name"],
                "result": deepcopy(result),
                "observation_chars": observation_chars,
                "observation_tokens": observation_tokens,
                "latency_ms": latency_ms,
                "ok": result.get("ok"),
                "error_code": error_code,
                # Backward-compatible names used by the existing D2 tables.
                "return_characters": observation_chars,
                "return_tokens_estimated_chars_div_4": observation_tokens,
            }
        )

    def finish_call(
        self,
        call: dict[str, Any],
        *,
        observation_tokens: int = 0,
        observation_chars: int = 0,
        latency_ms: float,
        ok: bool,
        error_code: str | None,
    ) -> None:
        """Attach execution metrics to the previously logged tool call."""
        for item in reversed(self.tool_calls):
            if item.get("id") == call.get("id"):
                item.update(
                    observation_tokens=observation_tokens,
                    observation_chars=observation_chars,
                    latency_ms=latency_ms,
                    ok=ok,
                    error_code=error_code,
                )
                return
        raise ValueError("Cannot finish an unknown tool call.")

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
