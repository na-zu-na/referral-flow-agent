"""Strict JSON contracts shared by scripted and live backends."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any


class BackendError(RuntimeError):
    """The provider request failed or returned an unusable envelope."""


class InvalidModelOutput(ValueError):
    """The model output is JSON but not a valid AgentMove."""


DECISIONS = {"book", "request_information", "escalate"}
TRIGGERS = {
    "red_flag_term",
    "specialty_mismatch",
    "duplicate_future_appointment",
    "no_slot_in_window",
    "instruction_in_referral_free_text",
    "tool_failure",
    "guardrail_stop",
}


def validate_move(value: Any) -> dict[str, Any]:
    """Validate and defensively copy one backend-produced AgentMove."""
    if not isinstance(value, dict):
        raise InvalidModelOutput("AgentMove must be a JSON object.")
    move_type = value.get("type")
    if move_type == "tool_calls":
        allowed = {"type", "thought", "calls"}
        if not set(value) <= allowed:
            raise InvalidModelOutput("tool_calls contains unknown fields.")
        calls = value.get("calls")
        if not isinstance(calls, list) or not calls:
            raise InvalidModelOutput("tool_calls requires a non-empty calls array.")
        for call in calls:
            _validate_tool_call(call)
        thought = value.get("thought")
        if thought is not None and not isinstance(thought, str):
            raise InvalidModelOutput("thought must be a string when present.")
        return deepcopy(value)
    if move_type == "final":
        return _validate_final(value)
    raise InvalidModelOutput("AgentMove type must be 'tool_calls' or 'final'.")


def parse_json_move(text: str) -> dict[str, Any]:
    """Parse a JSON-only response, accepting a single fenced JSON block."""
    if not isinstance(text, str) or not text.strip():
        raise InvalidModelOutput("Model returned empty content.")
    candidate = text.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3:
            candidate = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise InvalidModelOutput(f"Model did not return parseable JSON: {exc.msg}.") from exc
    return validate_move(value)


def _validate_tool_call(call: Any) -> None:
    if not isinstance(call, dict) or set(call) != {"id", "name", "arguments"}:
        raise InvalidModelOutput("Each ToolCall requires exactly id, name, and arguments.")
    if not isinstance(call["id"], str) or not call["id"]:
        raise InvalidModelOutput("ToolCall id must be a non-empty string.")
    if not isinstance(call["name"], str) or not call["name"]:
        raise InvalidModelOutput("ToolCall name must be a non-empty string.")
    if not isinstance(call["arguments"], dict):
        raise InvalidModelOutput("ToolCall arguments must be an object.")
    forbidden = {"_state", "_call_id", "confirmed", "approved", "safety_passed"}
    if forbidden & set(call["arguments"]):
        raise InvalidModelOutput("ToolCall contains controller-only arguments.")
    try:
        json.dumps(call["arguments"])
    except (TypeError, ValueError) as exc:
        raise InvalidModelOutput("ToolCall arguments must be JSON serializable.") from exc


def _validate_final(value: dict[str, Any]) -> dict[str, Any]:
    common = {"type", "decision", "reason"}
    decision = value.get("decision")
    if decision not in DECISIONS:
        raise InvalidModelOutput("Final decision is invalid.")
    if not isinstance(value.get("reason"), str) or not value["reason"].strip():
        raise InvalidModelOutput("Final reason must be a non-empty string.")
    if decision == "book":
        if set(value) != common | {"booked"}:
            raise InvalidModelOutput("Book final requires exactly a booked object.")
        booked = value.get("booked")
        if not isinstance(booked, dict) or set(booked) != {"clinic", "date", "time"}:
            raise InvalidModelOutput("booked requires exactly clinic, date, and time.")
        if not all(isinstance(item, str) and item for item in booked.values()):
            raise InvalidModelOutput("Every booked field must be a non-empty string.")
    elif decision == "request_information":
        if set(value) != common | {"missing"}:
            raise InvalidModelOutput("request_information requires exactly missing.")
        if not isinstance(value.get("missing"), str) or not value["missing"].strip():
            raise InvalidModelOutput("missing must name the exact missing item.")
    else:
        allowed = common | {"trigger", "escalate_to"}
        if not common | {"trigger"} <= set(value) or not set(value) <= allowed:
            raise InvalidModelOutput("escalate requires trigger and optional escalate_to.")
        if value.get("trigger") not in TRIGGERS:
            raise InvalidModelOutput("Escalation trigger is invalid.")
        if "escalate_to" in value and (
            not isinstance(value["escalate_to"], str) or not value["escalate_to"]
        ):
            raise InvalidModelOutput("escalate_to must be a non-empty string.")
    return deepcopy(value)
