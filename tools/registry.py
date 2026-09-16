"""Small, JSON-only boundary between the agent and its tools."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable, Mapping
from copy import deepcopy
from typing import Any

Tool = Callable[..., dict[str, Any]]
REGISTRY: dict[str, Tool] = {}

_READ_ONLY = {"value": "no", "gate": "none; the tool does not mutate state"}

_BASE_DESCRIPTORS = {
    "book_slot": {
        "name": "book_slot",
        "signature": "book_slot(referral_id: str, clinic: str, specialty: str, band: str, date: str, time: str) -> ToolResult",
        "what": "Commit one simulated outpatient appointment. Call alone and last, after referral, criteria, patient, and matching-slot evidence exists.",
        "input": {
            name: {
                "type": "string",
                "required": True,
                "constraints": constraint,
                "bad_value": "INVALID_BOOKING_ARGUMENTS or BOOKING_GATE_NOT_SATISFIED; no booking is written",
            }
            for name, constraint in {
                "referral_id": "exact id from get_referral",
                "clinic": "exact clinic from the selected slot",
                "specialty": "must match referral, criteria, and slot",
                "band": "urgent, soon, or routine; must match criteria and slot",
                "date": "ISO date inside the assessed window and selected slot",
                "time": "HH:MM time from the selected slot",
            }.items()
        },
        "returns": {
            "shape": {"ok": True, "data": {"booked": True, "referral_id": "string", "clinic": "string", "specialty": "string", "band": "string", "date": "YYYY-MM-DD", "time": "HH:MM", "capacity_remaining_after": "integer >= 0"}},
            "size_bound": "exactly one booking object; no fixture rows are returned",
        },
        "fails_when": [
            "BOOKING_AUTHORIZATION_REQUIRED when controller state or prepared call id is absent",
            "BOOKING_GATE_NOT_SATISFIED when evidence, dependency, autonomy, or trusted confirmation checks fail",
            "REFERRAL_NOT_FOUND, SPECIALTY_MISMATCH, DUPLICATE_BOOKING, SLOT_NOT_FOUND, or SLOT_FULL",
        ],
        "irreversible": {
            "value": "yes",
            "gate": "controller-only _state/_call_id plus autonomy policy; confirm mode requires a trusted approval callback and all evidence checks",
        },
    },
    "get_referral": {
        "name": "get_referral",
        "signature": "get_referral(referral_id: str) -> ToolResult",
        "what": "Fetch one stored referral. Call first and alone; later tools use its patient id, specialty, tests, and untrusted clinical summary.",
        "input": {
            "referral_id": {
                "type": "string",
                "required": True,
                "constraints": "non-empty exact referral id, for example REF-5602",
                "bad_value": "INVALID_REFERRAL_ID; a well-formed unknown id returns REFERRAL_NOT_FOUND",
            }
        },
        "returns": {
            "shape": {"ok": True, "data": "one Referral object as stored, including tests_attached and optional tests_attached_on"},
            "size_bound": "exactly one referral object; never a list",
        },
        "fails_when": ["INVALID_REFERRAL_ID", "REFERRAL_NOT_FOUND", "DATA_FILE_ERROR or DATA_INVALID_JSON"],
        "irreversible": _READ_ONLY,
    },
    "check_referral_criteria": {
        "name": "check_referral_criteria",
        "signature": "check_referral_criteria(referral_id: str, specialty: str) -> ToolResult",
        "what": "After get_referral, return protocol facts for hostile text, red flags, department fit, mandatory tests, urgency, and legal window. It may share a turn with lookup_patient and never makes the final decision.",
        "input": {
            "referral_id": {
                "type": "string",
                "required": True,
                "constraints": "non-empty exact id already returned by get_referral",
                "bad_value": "INVALID_REFERRAL_ID; unknown id returns REFERRAL_NOT_FOUND",
            },
            "specialty": {
                "type": "string",
                "required": True,
                "constraints": "non-empty exact specialty code on the referral",
                "bad_value": "INVALID_SPECIALTY, SPECIALTY_ARGUMENT_MISMATCH, or SPECIALTY_NOT_FOUND",
            },
        },
        "returns": {
            "shape": {"ok": True, "data": {"hostile_input_detected": "boolean", "hostile_matches": "list[string]", "red_flags_detected": "list[string]", "right_department": "boolean", "department_terms_detected": "list[string]", "mandatory_tests": "list[Test]", "missing_tests": "list[Test]", "band": "urgent|soon|routine", "urgency_terms_detected": "list[string]", "window_weeks": "integer", "window_start": "YYYY-MM-DD", "window_end": "YYYY-MM-DD"}},
            "size_bound": "one criteria object; lists are bounded by the selected specialty and urgency fixture records",
        },
        "fails_when": ["INVALID_REFERRAL_ID", "INVALID_SPECIALTY", "REFERRAL_NOT_FOUND", "SPECIALTY_ARGUMENT_MISMATCH", "SPECIALTY_NOT_FOUND", "DATA_INVALID_RECORD or data-store error"],
        "irreversible": _READ_ONLY,
    },
    "lookup_patient": {
        "name": "lookup_patient",
        "signature": "lookup_patient(patient_id: str) -> ToolResult",
        "what": "After get_referral, fetch the patient, appointment history, and directly joined contact. It may share a turn with check_referral_criteria.",
        "input": {
            "patient_id": {
                "type": "string",
                "required": True,
                "constraints": "non-empty exact patient id from get_referral",
                "bad_value": "INVALID_PATIENT_ID; unknown id returns PATIENT_NOT_FOUND",
            }
        },
        "returns": {
            "shape": {"ok": True, "data": {"patient": "one Patient object including existing_appointments", "contact": "one Contact object or null"}},
            "size_bound": "one patient and at most one joined contact; appointment count is bounded by that patient fixture row",
        },
        "fails_when": ["INVALID_PATIENT_ID", "PATIENT_NOT_FOUND", "DATA_FILE_ERROR or DATA_INVALID_JSON"],
        "irreversible": _READ_ONLY,
    },
}

_SLOTS_INPUT_V1 = {
    name: {"type": type_name, "required": name != "limit", "constraints": rule, "bad_value": error}
    for name, type_name, rule, error in (
        ("specialty", "string", "specialty code", "INVALID_SPECIALTY or SPECIALTY_NOT_FOUND"),
        ("band", "string", "urgency band", "INVALID_URGENCY_BAND"),
        ("window_start", "string", "start date", "INVALID_DATE_WINDOW"),
        ("window_end", "string", "end date", "INVALID_DATE_WINDOW"),
        ("limit", "integer", "optional maximum results; default 5", "INVALID_LIMIT"),
    )
}

_SLOTS_V1 = {
    "name": "get_clinic_slots",
    "signature": "get_clinic_slots(specialty: str, band: str, window_start: str, window_end: str, limit: int = 5) -> ToolResultV1",
    "what": "Find available clinic slots after referral checks pass.",
    "input": _SLOTS_INPUT_V1,
    "returns": {
        "shape": {"ok": True, "data": {"result": "SLOTS_FOUND|NO_SLOT_WITHIN_WINDOW", "slots": "list[Slot]"}},
        "size_bound": "at most limit slots; implementation rejects limit outside 1..20",
    },
    "fails_when": ["invalid specialty, urgency band, date window, or limit", "data-store error; no slots is a successful empty result"],
    "irreversible": _READ_ONLY,
}

_SLOTS_V2 = {
    "name": "get_clinic_slots",
    "signature": "get_clinic_slots(specialty: str, band: str, window_start: str, window_end: str, limit: int = 5) -> ToolResultV2",
    "what": "Only after criteria and duplicate checks pass, return sorted free slots matching the exact specialty and assessed band inside the legal clinical window. Never widen or drop constraints.",
    "input": {
        "specialty": {"type": "string", "required": True, "constraints": "non-empty exact code from get_referral", "bad_value": "INVALID_SPECIALTY or SPECIALTY_NOT_FOUND"},
        "band": {"type": "string", "required": True, "constraints": "exact urgent, soon, or routine value from check_referral_criteria", "bad_value": "INVALID_URGENCY_BAND"},
        "window_start": {"type": "string", "required": True, "constraints": "ISO date equal to the criteria window start and not before as_of", "bad_value": "INVALID_DATE_WINDOW"},
        "window_end": {"type": "string", "required": True, "constraints": "ISO date equal to the criteria deadline and no later than the band's legal end", "bad_value": "INVALID_DATE_WINDOW"},
        "limit": {"type": "integer", "required": False, "default": 5, "constraints": "1..20 inclusive", "bad_value": "INVALID_LIMIT"},
    },
    "returns": {
        "shape": {"ok": True, "data": {"result": "SLOTS_FOUND|NO_SLOT_WITHIN_WINDOW", "requested_window": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}, "slots": "list[{clinic, specialty, band, date, time, capacity_remaining}]"}},
        "size_bound": "0..limit sorted slots, with limit <= 20; only positive-capacity slots are returned",
    },
    "fails_when": ["INVALID_SPECIALTY", "SPECIALTY_NOT_FOUND", "INVALID_URGENCY_BAND", "INVALID_DATE_WINDOW", "INVALID_LIMIT", "data-store error; NO_SLOT_WITHIN_WINDOW is a successful business fact"],
    "irreversible": _READ_ONLY,
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
    descriptor_version: str = "v2",
) -> dict[str, Any]:
    """Validate, dispatch, and validate one agent-requested tool call."""
    if not isinstance(name, str) or name not in REGISTRY:
        return failure("UNKNOWN_TOOL", f"Tool {name!r} is not available.")
    if not isinstance(arguments, Mapping):
        return failure("INVALID_ARGUMENTS", "Tool arguments must be a JSON object.")

    if descriptor_version not in {"v1", "v2"}:
        return failure("INVALID_DESCRIPTOR_VERSION", "Descriptor version must be 'v1' or 'v2'.")

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
    result = _shape_result(name, result, descriptor_version)
    try:
        json.dumps(result)
    except (TypeError, ValueError):
        return failure("TOOL_PROTOCOL_ERROR", f"Tool {name!r} returned non-JSON data.")
    return result


def _shape_result(
    name: str, result: dict[str, Any], descriptor_version: str
) -> dict[str, Any]:
    """Apply the controller-selected D2(b) observation contract."""
    if (
        name == "get_clinic_slots"
        and descriptor_version == "v1"
        and result.get("ok") is True
        and isinstance(result.get("data"), dict)
    ):
        data = result["data"]
        return success({"result": data.get("result"), "slots": data.get("slots", [])})
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
