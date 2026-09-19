import json
import re
from collections import defaultdict


def optional_float(value):
    if value is None or str(value).strip() in {"", "None", "null"}:
        return None
    return float(value)


def optional_int(value):
    x = optional_float(value)
    return None if x is None else int(x)


def as_bool(value) -> bool:
    if str(value).lower() not in {"true", "false"}:
        raise ValueError(f"Expected boolean, got {value!r}")
    return str(value).lower() == "true"


def offline_lexical_unit_count(text: str) -> int:
    """Unicode word/punctuation segmentation, regex [\\w]+|[^\\w\\s].

    A deterministic local reference unit; NOT_PROVIDER_TOKENIZATION.
    """
    return len(re.findall(r"[\w]+|[^\w\s]", text, flags=re.UNICODE))


def normalized_runs(batteries: dict) -> list[dict]:
    from .loaders import score_rows
    audited = score_rows()
    scores = {row["run_id"]: row for row in audited}
    if len(audited) != 278 or len(scores) != 278:
        raise ValueError("Frozen D5 normalized score evidence must contain 278 unique runs")
    out = []
    for bid, d in batteries.items():
        for row in d["runs"]:
            score = scores.get(row["run_id"])
            if score is None or score["experiment_id"] != bid:
                raise ValueError(f"D5 score audit missing/mismatched run: {row['run_id']}")
            if score["changed"].lower() != "false" or score["original_passed"].lower() != score["normalized_passed"].lower():
                raise ValueError("Frozen D5 score change is not zero")
            if score["original_passed"].lower() != row["passed"].lower():
                raise ValueError("Frozen D5 scored run and final audit disagree")
            measured = as_bool(row["tokens_measured"])
            reported = optional_float(row["provider_cost_usd"])
            if not measured or reported is None:
                raise ValueError(f"Selected D5 provider usage/cost missing: {row['run_id']}")
            if float(score["provider_cost_usd"]) != reported or int(score["input_tokens"]) != int(row["tokens_in"]) or int(score["output_tokens"]) != int(row["tokens_out"]):
                raise ValueError("Frozen D5 cost/token fields disagree")
            out.append({
                "experiment_id": bid, "run_id": row["run_id"], "timestamp": row["timestamp"],
                "case_id": row["case_id"], "trial": int(row["trial"]), "model": row["model"],
                "scope": d["inventory"]["scope"], "family": d["inventory"]["family"],
                "team_price_tier": d["inventory"]["team_price_tier"],
                "prompt_version": row["prompt_version"], "descriptor_version": row["descriptor_version"],
                "backend": row["backend"], "execution_mode": row["execution_mode"],
                "negative_case": as_bool(row["negative_case"]), "expected_decision": row["expected_decision"],
                "actual_decision": row["decision"] or None, "passed": as_bool(score["normalized_passed"]),
                "failure_reason": score["normalized_failure_reason"] or None, "status": row["status"],
                "unsafe_book_slot_attempt": as_bool(score["unsafe_book_slot_attempt"]),
                "turns": int(row["turns"]),
                "input_tokens": optional_int(row["tokens_in"]) if measured else None,
                "output_tokens": optional_int(row["tokens_out"]) if measured else None,
                "cached_input_tokens": optional_int(row["cached_input_tokens"]) if measured else None,
                "reasoning_tokens": optional_int(row["reasoning_tokens"]) if measured else None,
                "tokens_measured": measured, "usage_measurement_status": "PROVIDER_REPORTED" if measured else "NOT_MEASURED",
                "provider_cost_usd": reported,
                "provider_cost_measurement_status": "PROVIDER_REPORTED" if reported is not None else "UNKNOWN",
                "latency_ms": optional_float(row["latency_ms"]), "error": row["error"] or None,
                "temperature": optional_float(row["temperature"]), "autonomy": row["autonomy"],
                "prompt_hash": row["prompt_hash"],
            })
    if len(out) != len(scores):
        raise ValueError("Selected D5 run audit not fully ingested")
    return out


def normalized_tool_calls(batteries: dict) -> list[dict]:
    out = []
    for bid, d in batteries.items():
        for wrapper in d["raw"]:
            record = wrapper["record"]
            observed = defaultdict(list)
            for o in record.get("observations", []):
                observed[str(o.get("call_id"))].append(o)
            for i, call in enumerate(record.get("tool_calls", []), 1):
                cid = str(call.get("id"))
                matching = observed.get(cid, [])
                obs = matching.pop(0) if matching else None
                payload = obs.get("result") if obs else None
                serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) if payload is not None else None
                out.append({
                    "experiment_id": bid, "run_id": record["run_id"], "case_id": wrapper["case_id"],
                    "trial": wrapper["trial"], "call_ordinal": i, "turn": call.get("turn"),
                    "tool_name": call.get("name"), "call_id": cid,
                    "arguments_json": json.dumps(call.get("arguments"), sort_keys=True, separators=(",", ":")),
                    "descriptor_version": record["descriptor_version"],
                    "ok": call.get("ok"), "error_code": call.get("error_code"),
                    "latency_ms": call.get("latency_ms"),
                    "observation_chars_local": call.get("observation_chars"),
                    "observation_size_local_estimated_chars_div_4": call.get("observation_tokens"),
                    "observation_size_local_status": "ESTIMATED" if obs else "NOT_MEASURED",
                    "observation_chars_recomputed": len(serialized) if serialized is not None else None,
                    "recomputed_chars_match_local": (len(serialized)==call.get("observation_chars")) if serialized is not None else None,
                    "observation_offline_lexical_units_recomputed": offline_lexical_unit_count(serialized) if serialized is not None else None,
                    "recomputed_measurement_status": "RECOMPUTED_FROM_SAVED_PAYLOAD" if serialized is not None else "NOT_MEASURED",
                    "provider_tokenization_status": "NOT_PROVIDER_TOKENIZATION",
                    "reference_segmentation_method": "Unicode regex [\\w]+|[^\\w\\s] on json.dumps(sort_keys=True,separators=(',',':'),ensure_ascii=True)",
                    "observation_payload_saved": payload is not None,
                })
    return out
