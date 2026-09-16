"""Single-agent ReAct controller: model -> tools -> observations -> model."""

from __future__ import annotations

import time
from copy import deepcopy
from datetime import date
from typing import Any, Callable

from backends import Backend, make_backend
from config import RunConfig
from guardrails import ConfirmationRequired, GuardrailState, GuardrailStop
from prompt import build_system_prompt
from tools import call_tool

from .schemas import BackendError, InvalidModelOutput, validate_move
from .trace import RunTrace

ApprovalCallback = Callable[[dict[str, Any]], bool]


def run_case(
    case_id: str,
    config: RunConfig | None = None,
    *,
    approve: ApprovalCallback | None = None,
    backend: Backend | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run one referral from a completely fresh controller and safety state.

    ``approve`` is a trusted Controller/UI callback.  Model arguments can never
    approve a booking.  For reproducible scripted runs only, omission selects a
    deterministic test approval policy; live runs pause when no callback exists.
    """
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("case_id must be a non-empty string.")
    settings = config or RunConfig.from_env()
    state = GuardrailState(
        max_turns=settings.max_turns,
        max_tokens=settings.max_tokens,
        autonomy=settings.autonomy,
    )
    trace = RunTrace(
        transcript=[
            {
                "role": "user",
                "content": {
                    "task": "Coordinate this outpatient referral.",
                    "referral_id": case_id,
                },
            }
        ]
    )
    started = time.perf_counter()
    final: dict[str, Any] | None = None
    status = "completed"
    stopped_by: dict[str, Any] | None = None
    error: dict[str, str] | None = None
    usage_flags: list[bool] = []
    provider_costs: list[float] = []

    try:
        controller = make_backend(
            case_id,
            settings,
            build_system_prompt(
                settings.descriptor_version,
                settings.call_mode,
                settings.prompt_version,
            ),
            backend=backend,
        )
        for iteration in range(1, settings.implementation_iteration_cap + 1):
            response = controller.next_move(deepcopy(trace.transcript))
            move, usage = _validate_backend_response(response)
            state.add_tokens(usage["input_tokens"], usage["output_tokens"])
            usage_flags.append(usage["measured"])
            if usage.get("provider_cost_usd") is not None:
                provider_costs.append(usage["provider_cost_usd"])
            trace.add_move(move)
            if verbose:
                _print_move(iteration, state.turns, move)

            if move["type"] == "final":
                _validate_final_against_evidence(move, state)
                trace.append_model_move(move)
                final = {key: deepcopy(value) for key, value in move.items() if key != "type"}
                break

            calls = move["calls"]
            state.prepare_turn(calls)
            trace.append_model_move(move)
            observations = []
            for call in calls:
                trace.add_call(state.turns, call)
                result = _execute_call(call, state, settings, approve)
                trace.add_observation(state.turns, call, result)
                state.record_observation(call, result)
                observation = {
                    "call_id": call["id"],
                    "name": call["name"],
                    "result": deepcopy(result),
                }
                observations.append(observation)
                if verbose:
                    print(f"    {call['name']}: {'ok' if result['ok'] else 'error'}")
            trace.append_observations(observations)
        else:
            status = "guardrail_stopped"
            stopped_by = {
                "type": "controller_stop",
                "code": "IMPLEMENTATION_ITERATION_CAP",
                "message": "Backend did not conclude before the controller iteration cap.",
                "terminal": True,
            }
            final = _safe_stop_final(stopped_by)
    except ConfirmationRequired as pause:
        status = "confirmation_required"
        stopped_by = pause.to_event()
    except GuardrailStop as stop:
        status = "guardrail_stopped"
        stopped_by = stop.to_event()
        final = _safe_stop_final(stopped_by)
    except InvalidModelOutput as exc:
        status = "invalid_model_output"
        error = {"type": type(exc).__name__, "message": str(exc)}
    except BackendError as exc:
        status = "backend_error"
        error = {"type": type(exc).__name__, "message": str(exc)}

    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    calculated_cost = (
        state.tokens_in / 1_000_000 * settings.price_input_per_million
        + state.tokens_out / 1_000_000 * settings.price_output_per_million
    )
    cost_usd = sum(provider_costs) if provider_costs else calculated_cost
    backend_name = getattr(locals().get("controller", backend), "name", settings.backend)
    model_name = getattr(locals().get("controller", backend), "model", settings.model)
    return {
        "case_id": case_id,
        "status": status,
        "backend": backend_name,
        "model": model_name,
        "prompt_version": settings.prompt_version,
        "descriptor_version": settings.descriptor_version,
        "call_mode": settings.call_mode,
        "autonomy": settings.autonomy,
        "final": final,
        "turns": state.turns,
        "iterations": len(trace.moves),
        "tool_calls": trace.tool_calls,
        "observations": trace.observations,
        "guardrail_events": deepcopy(state.events),
        "stopped_by": stopped_by,
        "tokens_in": state.tokens_in,
        "tokens_out": state.tokens_out,
        "tokens_measured": bool(usage_flags) and all(usage_flags),
        "cost_usd": round(cost_usd, 8),
        "duration_ms": duration_ms,
        "error": error,
        "transcript": trace.transcript,
        "moves": trace.moves,
    }


def _execute_call(
    call: dict[str, Any],
    state: GuardrailState,
    settings: RunConfig,
    approve: ApprovalCallback | None,
) -> dict[str, Any]:
    if call["name"] != "book_slot":
        return call_tool(call["name"], call["arguments"])
    try:
        return call_tool(
            call["name"], call["arguments"], state=state, call_id=call["id"]
        )
    except ConfirmationRequired as pause:
        callback = approve
        if callback is None and settings.backend == "scripted":
            callback = _scripted_test_approval
        if callback is None or callback(pause.to_event()) is not True:
            raise
        state.approve(call["id"])
        return call_tool(
            call["name"], call["arguments"], state=state, call_id=call["id"]
        )


def _scripted_test_approval(event: dict[str, Any]) -> bool:
    """Trusted deterministic policy used only by the offline replay backend."""
    return (
        event.get("type") == "confirmation_required"
        and event.get("call", {}).get("name") == "book_slot"
    )


def _validate_backend_response(response: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(response, dict) or set(response) != {"move", "usage"}:
        raise InvalidModelOutput("BackendResponse requires exactly move and usage.")
    move = validate_move(response["move"])
    usage = response["usage"]
    if not isinstance(usage, dict):
        raise InvalidModelOutput("Backend usage must be an object.")
    required = {"input_tokens", "output_tokens", "measured"}
    allowed = required | {"provider_cost_usd"}
    if not required <= set(usage) or not set(usage) <= allowed:
        raise InvalidModelOutput("Backend usage fields are invalid.")
    for name in ("input_tokens", "output_tokens"):
        value = usage[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise InvalidModelOutput(f"usage.{name} must be a non-negative integer.")
    if not isinstance(usage["measured"], bool):
        raise InvalidModelOutput("usage.measured must be boolean.")
    cost = usage.get("provider_cost_usd")
    if cost is not None and (
        isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0
    ):
        raise InvalidModelOutput("usage.provider_cost_usd must be non-negative.")
    return move, deepcopy(usage)


def _validate_final_against_evidence(final: dict[str, Any], state: GuardrailState) -> None:
    decision = final["decision"]
    observations = list(state.observations.values())
    if decision == "book":
        expected = final["booked"]
        matching = [
            item["result"]["data"]
            for item in observations
            if item["call"]["name"] == "book_slot"
            and item["result"].get("ok") is True
            and isinstance(item["result"].get("data"), dict)
        ]
        if not any(
            all(result.get(key) == expected[key] for key in ("clinic", "date", "time"))
            for result in matching
        ):
            raise InvalidModelOutput("Book final is not supported by a successful book_slot.")
        return
    if decision == "request_information":
        missing = final["missing"].lower()
        tests = [
            test
            for item in observations
            if item["call"]["name"] == "check_referral_criteria"
            and item["result"].get("ok") is True
            for test in item["result"].get("data", {}).get("missing_tests", [])
            if isinstance(test, dict)
        ]
        if not any(
            bool(test.get("code"))
            and bool(test.get("name"))
            and str(test["code"]).lower() in missing
            and str(test["name"]).lower() in missing
            for test in tests
        ):
            raise InvalidModelOutput("Missing-test final is not supported by criteria evidence.")
        return
    trigger = final["trigger"]
    if not _escalation_supported(trigger, observations):
        raise InvalidModelOutput(f"Escalation trigger {trigger!r} is not supported by evidence.")


def _escalation_supported(trigger: str, observations: list[dict[str, Any]]) -> bool:
    criteria = [
        item["result"].get("data", {})
        for item in observations
        if item["call"]["name"] == "check_referral_criteria"
        and item["result"].get("ok") is True
    ]
    if trigger == "red_flag_term":
        return any(data.get("red_flags_detected") for data in criteria)
    if trigger == "specialty_mismatch":
        return any(data.get("right_department") is False for data in criteria)
    if trigger == "instruction_in_referral_free_text":
        return any(data.get("hostile_input_detected") is True for data in criteria)
    if trigger == "duplicate_future_appointment":
        referrals = [
            item["result"].get("data", {})
            for item in observations
            if item["call"]["name"] == "get_referral"
            and item["result"].get("ok") is True
        ]
        patients = [
            item["result"].get("data", {}).get("patient", {})
            for item in observations
            if item["call"]["name"] == "lookup_patient"
            and item["result"].get("ok") is True
        ]
        if not referrals or not criteria or not patients:
            return False
        referral = referrals[-1]
        criterion = criteria[-1]
        patient = patients[-1]
        if patient.get("patient_id") != referral.get("patient_id"):
            return False
        try:
            clock = date.fromisoformat(criterion["window_start"])
        except (KeyError, TypeError, ValueError):
            return False
        for appointment in patient.get("existing_appointments", []):
            if not isinstance(appointment, dict):
                return False
            if appointment.get("specialty") != referral.get("specialty"):
                continue
            try:
                if date.fromisoformat(appointment["date"]) > clock:
                    return True
            except (KeyError, TypeError, ValueError):
                return False
        return False
    if trigger == "no_slot_in_window":
        return any(
            item["call"]["name"] == "get_clinic_slots"
            and item["result"].get("ok") is True
            and item["result"].get("data", {}).get("result") == "NO_SLOT_WITHIN_WINDOW"
            for item in observations
        )
    if trigger == "tool_failure":
        return any(item["result"].get("ok") is False for item in observations)
    return False


def _safe_stop_final(event: dict[str, Any]) -> dict[str, Any]:
    hostile = event.get("code") == "HOSTILE_INPUT_DETECTED"
    return {
        "decision": "escalate",
        "reason": event.get("message", "A deterministic safety control stopped the run."),
        "trigger": (
            "instruction_in_referral_free_text" if hostile else "guardrail_stop"
        ),
        "escalate_to": "triage nurse" if hostile else "system owner",
    }


def _print_move(iteration: int, completed_turns: int, move: dict[str, Any]) -> None:
    label = "final" if move["type"] == "final" else f"turn {completed_turns + 1}"
    thought = move.get("thought", "")
    print(f"[{iteration}] {label}: {thought}")
