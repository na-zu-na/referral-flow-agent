"""Small, JSON-only boundary between the agent and its tools."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable, Mapping
from copy import deepcopy
from typing import Any

Tool = Callable[..., dict[str, Any]]
REGISTRY: dict[str, Tool] = {}

_BASE_DESCRIPTORS = {
    "book_slot": {
        "name": "book_slot",
        "purpose": "Commit one simulated outpatient appointment after every safety condition is proven.",
        "when": "Call alone, only after referral, criteria, patient, and matching slot observations exist. The tool enforces the Booking Gate; the controller must provide the prepared call and trusted human confirmation.",
        "arguments": {
            "referral_id": "Exact referral id supported by the stored evidence.",
            "clinic": "Clinic returned by get_clinic_slots.",
            "specialty": "Exact specialty from the referral and selected slot.",
            "band": "Exact urgency band from the criteria and selected slot.",
            "date": "Selected slot ISO date inside the assessed window.",
            "time": "Selected slot time.",
        },
        "returns": "A booking confirmation with clinic, specialty, band, date, time, and remaining simulated capacity.",
        "failure": "The call is blocked without trusted evidence and confirmation. It may also return REFERRAL_NOT_FOUND, SPECIALTY_MISMATCH, DUPLICATE_BOOKING, SLOT_NOT_FOUND, or SLOT_FULL.",
        "irreversible": True,
    },
    "get_referral": {
        "name": "get_referral",
        "purpose": "Fetch the referral identified by the case id.",
        "when": "Call first and alone. Later tools require its patient, specialty, tests, and clinical summary.",
        "arguments": {"referral_id": "Non-empty referral id, for example REF-5602."},
        "returns": "The stored referral, including optional tests_attached_on when present.",
        "failure": "REFERRAL_NOT_FOUND for an unknown id; INVALID_REFERRAL_ID for invalid input; data error codes when fixtures cannot be read.",
        "irreversible": False,
    },
    "get_system_date": {
        "name": "get_system_date",
        "purpose": "Read the fixed as_of date used to judge future appointments and booking windows.",
        "when": "Use when an independent clock value is needed. Do not substitute the referral date or the computer's current date.",
        "arguments": {},
        "returns": "An object containing as_of as an ISO date.",
        "failure": "DATA_INVALID_RECORD or a data-store error when the clock is unavailable.",
        "irreversible": False,
    },
    "check_referral_criteria": {
        "name": "check_referral_criteria",
        "purpose": "Report hostile text, specialty-specific red flags, department fit, missing tests, urgency band, and the legal booking window.",
        "when": "Call after get_referral. It may run in the same turn as lookup_patient because neither depends on the other.",
        "arguments": {
            "referral_id": "The referral id returned by the work queue.",
            "specialty": "The exact specialty code on that referral.",
        },
        "returns": "Protocol facts only; it never returns book, request_information, or escalate.",
        "failure": "REFERRAL_NOT_FOUND, SPECIALTY_NOT_FOUND, SPECIALTY_ARGUMENT_MISMATCH, invalid-input, or data error codes.",
        "irreversible": False,
    },
    "lookup_patient": {
        "name": "lookup_patient",
        "purpose": "Fetch the patient, existing appointments, and directly joined contact record.",
        "when": "Call after get_referral and before proposing a booking. Compare appointment specialty and date with the criteria window start to detect a future duplicate.",
        "arguments": {"patient_id": "The exact patient id from the referral."},
        "returns": "An object containing patient and contact. Past appointments remain present and are not automatically duplicates.",
        "failure": "PATIENT_NOT_FOUND for an unknown id; INVALID_PATIENT_ID for invalid input; data error codes when fixtures cannot be read.",
        "irreversible": False,
    },
}

_SLOTS_V1 = {
    "name": "get_clinic_slots",
    "purpose": "Find available clinic slots.",
    "when": "Use when a slot is needed.",
    "arguments": {
        "specialty": "Specialty code.",
        "band": "Urgency band.",
        "window_start": "Start date.",
        "window_end": "End date.",
        "limit": "Maximum results.",
    },
    "returns": "Available slots.",
    "failure": "Returns an error for invalid input or no slots when none are available.",
    "irreversible": False,
}

_SLOTS_V2 = {
    "name": "get_clinic_slots",
    "purpose": "Return up to limit free slots matching one specialty and urgency band inside a legal clinical window.",
    "when": "Call only after criteria and duplicate checks pass. Never drop the band, widen the window, or call after an early-stop condition.",
    "arguments": {
        "specialty": "Exact specialty code from the referral.",
        "band": "Required urgent, soon, or routine value returned by check_referral_criteria.",
        "window_start": "ISO date on or after as_of; use the criteria window start.",
        "window_end": "ISO date no later than the band deadline; use the criteria window end.",
        "limit": "Optional integer from 1 to 20; defaults to 5.",
    },
    "returns": "SLOTS_FOUND with sorted slots whose capacity_remaining is above zero, or NO_SLOT_WITHIN_WINDOW with an empty list.",
    "failure": "INVALID_DATE_WINDOW, INVALID_URGENCY_BAND, INVALID_LIMIT, SPECIALTY_NOT_FOUND, or a data-store error. No slot is a successful business fact, not a tool failure.",
    "irreversible": False,
}

DESCRIPTORS_V1 = {**_BASE_DESCRIPTORS, "get_clinic_slots": _SLOTS_V1}
DESCRIPTORS_V2 = {**_BASE_DESCRIPTORS, "get_clinic_slots": _SLOTS_V2}
DESCRIPTORS = DESCRIPTORS_V2


def get_descriptors(version: str = "v2") -> dict[str, dict[str, Any]]:
    """Return a safe copy of the descriptor set selected for an experiment."""
    versions = {"v1": DESCRIPTORS_V1, "v2": DESCRIPTORS_V2}
    if version not in versions:
        raise ValueError("Descriptor version must be 'v1' or 'v2'.")
    return deepcopy(versions[version])


def success(data: Any) -> dict[str, Any]:
    """Return a successful tool observation."""
    return {"ok": True, "data": data}


def failure(code: str, message: str) -> dict[str, Any]:
    """Return a structured tool failure."""
    return {"ok": False, "error": {"code": code, "message": message}}


def register_tool(name: str, function: Tool) -> None:
    """Register one callable under the exact name exposed to the agent."""
    if not name or not isinstance(name, str):
        raise ValueError("Tool name must be a non-empty string.")
    if not callable(function):
        raise TypeError("Tool must be callable.")
    if name in REGISTRY:
        raise ValueError(f"Tool {name!r} is already registered.")
    REGISTRY[name] = function


def call_tool(
    name: str,
    arguments: Mapping[str, Any],
    *,
    state: Any = None,
    call_id: str | None = None,
) -> dict[str, Any]:
    """Validate, dispatch, and validate one agent-requested tool call."""
    if not isinstance(name, str) or name not in REGISTRY:
        return failure("UNKNOWN_TOOL", f"Tool {name!r} is not available.")
    if not isinstance(arguments, Mapping):
        return failure("INVALID_ARGUMENTS", "Tool arguments must be a JSON object.")

    function = REGISTRY[name]
    kwargs = dict(arguments)
    if name == "book_slot":
        if state is None or not isinstance(call_id, str) or not call_id:
            return failure(
                "BOOKING_AUTHORIZATION_REQUIRED",
                "book_slot requires a prepared call id and GuardrailState.",
            )
        kwargs["_state"] = state
        kwargs["_call_id"] = call_id
    try:
        inspect.signature(function).bind(**kwargs)
    except TypeError:
        return failure("INVALID_ARGUMENTS", f"Arguments for tool {name!r} are invalid.")

    try:
        result = function(**kwargs)
    except Exception as exc:
        from guardrails import ConfirmationRequired, GuardrailStop

        if isinstance(exc, (ConfirmationRequired, GuardrailStop)):
            raise
        return failure("TOOL_EXECUTION_ERROR", f"Tool {name!r} failed to execute.")

    if not _valid_result(result):
        return failure("TOOL_PROTOCOL_ERROR", f"Tool {name!r} returned an invalid result.")
    try:
        json.dumps(result)
    except (TypeError, ValueError):
        return failure("TOOL_PROTOCOL_ERROR", f"Tool {name!r} returned non-JSON data.")
    return result


def _valid_result(result: Any) -> bool:
    if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
        return False
    if result["ok"]:
        return "data" in result and "error" not in result
    error = result.get("error")
    return (
        "data" not in result
        and isinstance(error, dict)
        and isinstance(error.get("code"), str)
        and bool(error["code"])
        and isinstance(error.get("message"), str)
        and bool(error["message"])
    )
