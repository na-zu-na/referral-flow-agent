"""Deterministic, per-run guardrails for tool execution."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

_DEPENDENCIES = {
    "check_referral_criteria": {"get_referral"},
    "lookup_patient": {"get_referral"},
    "get_clinic_slots": {"check_referral_criteria", "lookup_patient"},
    "book_slot": {"check_referral_criteria", "lookup_patient", "get_clinic_slots"},
}


class GuardrailStop(RuntimeError):
    """A terminal code-layer stop that the Agent Controller must not ignore."""

    def __init__(self, event: dict[str, Any]):
        self.event = event
        self.code = event["code"]
        super().__init__(event["message"])

    def to_event(self) -> dict[str, Any]:
        return deepcopy(self.event)


class ConfirmationRequired(RuntimeError):
    """A non-terminal pause while a trusted human approves an action."""

    def __init__(self, event: dict[str, Any]):
        self.event = event
        super().__init__(event["message"])

    def to_event(self) -> dict[str, Any]:
        return deepcopy(self.event)


class GuardrailState:
    """All guardrail state for exactly one Agent run."""

    def __init__(
        self,
        max_turns: int = 8,
        max_tokens: int = 60_000,
        autonomy: str = "confirm",
    ):
        if isinstance(max_turns, bool) or not isinstance(max_turns, int) or max_turns < 1:
            raise ValueError("max_turns must be a positive integer.")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer.")
        if autonomy not in {"suggest", "confirm", "act"}:
            raise ValueError("autonomy must be 'suggest', 'confirm', or 'act'.")

        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.autonomy = autonomy
        self.turns = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.seen_actions: set[str] = set()
        self.completed_tools: set[str] = set()
        self.prepared_calls: dict[str, dict[str, Any]] = {}
        self.observations: dict[str, dict[str, Any]] = {}
        self.approved_calls: set[str] = set()
        self.bookings: list[dict[str, Any]] = []
        self.slot_capacity_used: dict[str, int] = {}
        self.events: list[dict[str, Any]] = []
        self.terminal_event: dict[str, Any] | None = None

    @property
    def tokens_total(self) -> int:
        return self.tokens_in + self.tokens_out

    def prepare_turn(self, calls: list[dict[str, Any]]) -> None:
        """Validate one tool-calling turn before any call executes."""
        self._ensure_active()
        attempted_turn = self.turns + 1
        if attempted_turn > self.max_turns:
            self._stop(
                "STEP_LIMIT_REACHED",
                f"Run reached the {self.max_turns}-turn limit.",
            )
        if not isinstance(calls, list) or not calls:
            self._stop("INVALID_TOOL_CALL", "A tool-calling turn needs at least one call.")

        validated = [self._validate_call(call) for call in calls]
        call_ids = [call["id"] for call in validated]
        if len(call_ids) != len(set(call_ids)) or any(
            call_id in self.prepared_calls for call_id in call_ids
        ):
            self._stop("INVALID_TOOL_CALL", "Tool call ids must be unique within a run.")

        names = [call["name"] for call in validated]
        if len(validated) > 1 and ("get_referral" in names or "book_slot" in names):
            self._stop(
                "DEPENDENCY_VIOLATION",
                "get_referral and book_slot must each run alone.",
            )

        for call in validated:
            missing = _DEPENDENCIES.get(call["name"], set()) - self.completed_tools
            if missing:
                self._stop(
                    "DEPENDENCY_VIOLATION",
                    f"Tool {call['name']!r} requires completed evidence from: "
                    + ", ".join(sorted(missing))
                    + ".",
                    call["id"],
                )

        signatures = [_signature(call) for call in validated]
        if len(signatures) != len(set(signatures)) or any(
            signature in self.seen_actions for signature in signatures
        ):
            self._stop(
                "DUPLICATE_ACTION_BLOCKED",
                "A tool was repeated with identical arguments.",
            )

        self.turns = attempted_turn
        self.seen_actions.update(signatures)
        self.prepared_calls.update(
            {call["id"]: deepcopy(call) for call in validated}
        )

    def add_tokens(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Record measured usage and stop as soon as the ceiling is exceeded."""
        self._ensure_active()
        values = (input_tokens, output_tokens)
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
            self._stop("INVALID_TOKEN_USAGE", "Token usage must be non-negative integers.")
        self.tokens_in += input_tokens
        self.tokens_out += output_tokens
        if self.tokens_total > self.max_tokens:
            self._stop(
                "BUDGET_LIMIT_REACHED",
                f"Run used {self.tokens_total} tokens; limit is {self.max_tokens}.",
            )

    def record_observation(
        self, call: dict[str, Any], result: dict[str, Any]
    ) -> None:
        """Store trusted tool evidence; only successful calls unlock dependencies."""
        self._ensure_active()
        validated = self._validate_call(call)
        expected = self.prepared_calls.get(validated["id"])
        if expected != validated or validated["id"] in self.observations:
            self._stop(
                "UNEXPECTED_TOOL_OBSERVATION",
                "Observation does not match one prepared, unrecorded tool call.",
                validated["id"],
            )
        if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
            self._stop(
                "TOOL_PROTOCOL_ERROR",
                f"Tool {validated['name']!r} returned an invalid observation.",
                validated["id"],
            )
        self.observations[validated["id"]] = {
            "call": deepcopy(validated),
            "result": deepcopy(result),
        }
        if result["ok"]:
            self.completed_tools.add(validated["name"])
            data = result.get("data")
            if (
                validated["name"] == "check_referral_criteria"
                and isinstance(data, dict)
                and data.get("hostile_input_detected") is True
            ):
                self._stop(
                    "HOSTILE_INPUT_DETECTED",
                    "Untrusted referral text attempted to influence system behaviour.",
                    validated["id"],
                )

    def approve(self, call_id: str) -> None:
        """Record approval received through a trusted controller or UI."""
        self._ensure_active()
        if not isinstance(call_id, str) or not call_id:
            raise ValueError("call_id must be a non-empty string.")
        if call_id not in self.prepared_calls:
            raise ValueError("Only a prepared tool call can be approved.")
        self.approved_calls.add(call_id)

    def check_autonomy(self, call: dict[str, Any]) -> None:
        """Gate an irreversible call without trusting model-supplied arguments."""
        self._ensure_active()
        validated = self._validate_call(call)
        if self.prepared_calls.get(validated["id"]) != validated:
            self._stop(
                "UNEXPECTED_TOOL_CALL",
                "Autonomy gate received a call that was not prepared.",
                validated["id"],
            )
        if self.autonomy == "act":
            self._event("AUTONOMY_GATE_PASSED", "Action allowed by act autonomy.", validated["id"])
            return
        if self.autonomy == "suggest":
            self._stop(
                "AUTONOMY_SUGGEST_ONLY",
                "Suggest autonomy does not permit tool execution.",
                validated["id"],
            )
        if validated["id"] not in self.approved_calls:
            event = {
                "type": "confirmation_required",
                "code": "HUMAN_CONFIRMATION_REQUIRED",
                "message": "A trusted human must confirm the irreversible action.",
                "call": deepcopy(validated),
                "terminal": False,
            }
            self.events.append(deepcopy(event))
            raise ConfirmationRequired(event)
        self._event(
            "AUTONOMY_GATE_PASSED",
            "Action approved by a trusted human.",
            validated["id"],
        )

    def record_event(self, code: str, message: str, call_id: str | None = None) -> None:
        """Record a non-terminal event from another deterministic guardrail."""
        self._ensure_active()
        self._event(code, message, call_id)

    def block(self, code: str, message: str, call_id: str | None = None) -> None:
        """Raise a terminal stop from another deterministic guardrail."""
        self._ensure_active()
        self._stop(code, message, call_id)

    def _ensure_active(self) -> None:
        if self.terminal_event is not None:
            raise GuardrailStop(deepcopy(self.terminal_event))

    def _validate_call(self, call: Any) -> dict[str, Any]:
        if not isinstance(call, dict):
            self._stop("INVALID_TOOL_CALL", "Each tool call must be an object.")
        if set(call) != {"id", "name", "arguments"}:
            self._stop(
                "INVALID_TOOL_CALL",
                "Each tool call requires exactly id, name, and arguments.",
            )
        if not isinstance(call["id"], str) or not call["id"]:
            self._stop("INVALID_TOOL_CALL", "Tool call id must be a non-empty string.")
        if not isinstance(call["name"], str) or not call["name"]:
            self._stop("INVALID_TOOL_CALL", "Tool name must be a non-empty string.")
        if not isinstance(call["arguments"], dict):
            self._stop("INVALID_TOOL_CALL", "Tool arguments must be an object.")
        try:
            json.dumps(call["arguments"], sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError):
            self._stop("INVALID_TOOL_CALL", "Tool arguments must be JSON serializable.")
        return call

    def _event(self, code: str, message: str, call_id: str | None = None) -> None:
        event = {"type": "guardrail_event", "code": code, "message": message}
        if call_id is not None:
            event["call_id"] = call_id
        self.events.append(event)

    def _stop(self, code: str, message: str, call_id: str | None = None) -> None:
        event = {
            "type": "guardrail_stop",
            "code": code,
            "message": message,
            "terminal": True,
        }
        if call_id is not None:
            event["blocked_call_id"] = call_id
        self.terminal_event = deepcopy(event)
        self.events.append(deepcopy(event))
        raise GuardrailStop(event)


def _signature(call: dict[str, Any]) -> str:
    arguments = json.dumps(call["arguments"], sort_keys=True, separators=(",", ":"))
    return f"{call['name']}|{arguments}"
