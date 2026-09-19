"""Deterministic D6 pipeline. Reads only D5/repository; writes only D6/outputs."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal
from statistics import mean, median

import numpy as np

from .anomaly_detection import anomaly_rows, p95, thresholds
from .attribution import cost_levers
from .bootstrap import bootstrap_metrics
from .config import (BOOTSTRAP_ITERATIONS, BOOTSTRAP_SEED, D5, D6, FAILURE_COST_USD,
                     FIXED_MONTHLY_COST_USD, MONTHLY_REFERRALS, OUT, VALUE_OF_ONE_SUCCESS_PP_MONTHLY)
from .cost_engine import break_even, case_balanced_mean, fallback_cost, monthly_cost, pass_rates, sensitivity_rates
from .failure_analysis import category_counts, taxonomy_rows
from .governance import proposed_governance
from .loaders import inventory, load_batteries
from .normalization import normalized_runs, normalized_tool_calls
from .pareto import pareto_status
from .pricing import load_registry, recompute_list_rate_cost, verify_registry


def save_csv(name: str, rows: list[dict], fields: list[str] | None = None) -> None:
    if not rows and fields is None:
        raise ValueError(f"No rows for {name}")
    fields = fields or list(dict.fromkeys(key for row in rows for key in row))
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _summaries(runs: list[dict], taxonomy: list[dict], safety: dict) -> list[dict]:
    grouped = defaultdict(list)
    for r in runs:
        grouped[r["experiment_id"]].append(r)
    counts = category_counts(taxonomy)
    out = []
    for bid, rr in grouped.items():
        trial_p, case_p = pass_rates(rr)
        cost = [r["provider_cost_usd"] for r in rr if r["provider_cost_usd"] is not None]
        inputs = [r["input_tokens"] for r in rr if r["input_tokens"] is not None]
        outputs = [r["output_tokens"] for r in rr if r["output_tokens"] is not None]
        turns = [r["turns"] for r in rr]
        recomputed = [r["recomputed_ai_cost_usd"] for r in rr if r["recomputed_ai_cost_usd"] is not None]
        ai = mean(cost)
        scope = rr[0]["scope"]
        general = scope != "negative_only"
        case_ai, ai_cases, total_cases = case_balanced_mean(rr, "provider_cost_usd")
        case_input, input_cases, _ = case_balanced_mean(rr, "input_tokens")
        case_output, output_cases, _ = case_balanced_mean(rr, "output_tokens")
        case_turns, _, _ = case_balanced_mean(rr, "turns")
        case_invalid, _, _ = case_balanced_mean(rr, lambda r: r["status"]=="invalid_model_output")
        out.append({
            "experiment_id": bid, "model": rr[0]["model"], "prompt_version": rr[0]["prompt_version"],
            "scope": "FRONTIER_NEGATIVE_ONLY" if not general else scope.upper(),
            "family": rr[0]["family"], "price_tier": rr[0]["team_price_tier"].upper(),
            "descriptor_version": rr[0]["descriptor_version"], "runs": len(rr),
            "unique_cases": len({r["case_id"] for r in rr}),
            "passed_runs": sum(r["passed"] for r in rr), "failed_runs": sum(not r["passed"] for r in rr),
            "trial_weighted_pass_rate": trial_p if general else None,
            "case_balanced_pass_rate": case_p if general else None,
            "negative_subset_pass_rate": trial_p if not general else None,
            "overall_pass_rate_status": "EVALUATION_SET_ONLY" if general else "N/A_NEGATIVE_ONLY_SCOPE",
            "invalid_model_output_count": counts[bid]["INVALID_MODEL_OUTPUT"],
            "trial_weighted_invalid_output_rate": counts[bid]["INVALID_MODEL_OUTPUT"]/len(rr),
            "case_balanced_invalid_output_rate": case_invalid,
            "unsafe_action_count": safety[bid]["unsafe_booking_attempts"],
            "avg_input_tokens": mean(inputs), "median_input_tokens": median(inputs), "p95_input_tokens": p95(inputs),
            "case_balanced_avg_input_tokens": case_input,
            "case_balanced_input_token_case_coverage": f"{input_cases}/{total_cases}",
            "avg_output_tokens": mean(outputs), "median_output_tokens": median(outputs), "p95_output_tokens": p95(outputs),
            "case_balanced_avg_output_tokens": case_output,
            "case_balanced_output_token_case_coverage": f"{output_cases}/{total_cases}",
            "avg_turns": mean(turns), "median_turns": median(turns), "p95_turns": p95(turns),
            "case_balanced_avg_turns": case_turns,
            "descriptive_avg_median_p95_weighting": "TRIAL_WEIGHTED",
            "provider_cost_rows": len(cost), "provider_cost_coverage": f"{len(cost)}/{len(rr)}",
            "provider_spend_usd": float(sum((Decimal(str(value)) for value in cost), Decimal("0"))),
            "total_input_tokens": sum(inputs), "total_output_tokens": sum(outputs),
            "total_cached_input_tokens": sum(r["cached_input_tokens"] or 0 for r in rr),
            "total_reasoning_tokens": sum(r["reasoning_tokens"] or 0 for r in rr),
            "avg_provider_ai_cost_measured": ai,
            "case_balanced_ai_cost_per_referral": case_ai if general else None,
            "case_balanced_provider_cost_case_coverage": f"{ai_cases}/{total_cases}",
            "case_balanced_ai_cost_measurement_status": "PROVIDER_REPORTED" if general else "N/A_NEGATIVE_ONLY_SCOPE",
            "ai_cost_measurement_status": "PROVIDER_REPORTED",
            "recomputed_ai_cost": mean(recomputed) if recomputed else None,
            "recomputed_ai_cost_measurement_status": "RECOMPUTED_FROM_D5_CONFIG_LIST_RATE" if recomputed else "NOT_AVAILABLE",
            "trial_weighted_fallback_cost_per_referral": fallback_cost(trial_p) if general else None,
            "case_balanced_fallback_cost_per_referral": fallback_cost(case_p) if general else None,
            "fallback_measurement_status": "ASSUMED_ASSIGNMENT_NURSE_RATE_AND_TIME",
            "trial_weighted_total_cost_per_referral": ai+fallback_cost(trial_p) if general else None,
            "case_balanced_total_cost_per_referral": case_ai+fallback_cost(case_p) if general else None,
            "trial_weighted_monthly_cost": monthly_cost(ai, trial_p) if general else None,
            "case_balanced_monthly_cost": monthly_cost(case_ai, case_p) if general else None,
            "fixed_monthly_cost": float(FIXED_MONTHLY_COST_USD) if general else None,
            "fixed_cost_measurement_status": "BASELINE_ASSUMPTION_NOT_MEASURED" if general else "N/A_NEGATIVE_ONLY_SCOPE",
            "measurement_notes": "NEGATIVE_SUBSET_STRESS_TEST_NOT_PRODUCTION; no general monthly, sensitivity, break-even or Pareto" if not general else "Evaluation-rate scenario, not hospital prevalence; invalid outputs are failures; fixed deployment cost is unmeasured and zero only in baseline",
        })
    return out


def _safety(runs: list[dict], batteries: dict) -> tuple[list[dict], dict]:
    grouped = defaultdict(list)
    for r in runs:
        grouped[r["experiment_id"]].append(r)
    out, by_id = [], {}
    for bid, rr in grouped.items():
        raw = {w["record"]["run_id"]: w["record"] for w in batteries[bid]["raw"]}
        negative = [r for r in rr if r["negative_case"]]
        unsafe = [r for r in negative if any(c.get("name")=="book_slot" for c in raw[r["run_id"]].get("tool_calls", []))]
        negative_pass = sum(r["passed"] for r in negative)
        row = {"experiment_id": bid, "model": rr[0]["model"], "prompt_version": rr[0]["prompt_version"],
               "negative_trials": len(negative), "negative_passed": negative_pass,
               "negative_case_pass_rate": negative_pass/len(negative),
               "unsafe_booking_attempts": len(unsafe),
               "unsafe_action_definition": "book_slot tool attempted in an evaluation negative-case run",
               "measurement_status": "MEASURED_FROM_D5_RAW_TRACES",
               "monetary_penalty_usd": None,
               "monetary_penalty_status": "NOT_AVAILABLE_NO_DEFENSIBLE_ASSIGNMENT_VALUE"}
        out.append(row)
        by_id[bid] = row
    return out, by_id


def _spend(runs: list[dict], batteries: dict) -> tuple[list[dict], dict]:
    scored = sum((Decimal(str(r["provider_cost_usd"])) for r in runs if r["provider_cost_usd"] is not None), Decimal("0"))
    extra = sum((Decimal(str(e["record"]["provider_cost_usd"])) for d in batteries.values() for e in d["extra_errors"]), Decimal("0"))
    if (len(runs), sum(r["provider_cost_usd"] is not None for r in runs)) != (278,278):
        raise ValueError("Final selected cost coverage is not 278/278")
    vals = {"selected_scored_run_spend": scored,
            "extra_charged_mistral_provider_error": extra,
            "recorded_selected_model_charges_including_error": scored + extra}
    rows = [{"metric": key, "value_usd": str(value), "scope": "CURRENT_SELECTED_EVALUATION_SPEND",
             "measurement_status": "RECOMPUTED_FROM_FROZEN_D5_PROVIDER_CHARGES",
             "scored_run_denominator": 278 if key == "selected_scored_run_spend" else 0}
            for key,value in vals.items()]
    rows += [{"metric": "historical_account_increment", "value_usd": "0.653968992",
              "scope": "HISTORICAL_SUPERSEDED_ACCOUNT_SNAPSHOT_NOT_CURRENT_SELECTED_SPEND",
              "measurement_status": "DOCUMENT_REPORTED_HISTORICAL_CONTEXT", "scored_run_denominator": ""},
             {"metric": "historical_unattributed_residual", "value_usd": "0.018762122",
              "scope": "HISTORICAL_SUPERSEDED_ACCOUNT_SNAPSHOT_NOT_CURRENT_SELECTED_SPEND",
              "measurement_status": "DOCUMENT_REPORTED_HISTORICAL_CONTEXT", "scored_run_denominator": ""}]
    return rows, {k: float(v) for k,v in vals.items()}


def _qwen(summary: list[dict]) -> list[dict]:
    by = {x["experiment_id"]: x for x in summary}
    v1, v2 = by["qwen3_30b_v1"], by["qwen3_30b_v2"]
    out=[]
    for view in ("trial_weighted","case_balanced"):
        pass1=v1[f"{view}_pass_rate"]
        pass2=v2[f"{view}_pass_rate"]
        fall1=v1[f"{view}_fallback_cost_per_referral"]
        fall2=v2[f"{view}_fallback_cost_per_referral"]
        if view=="case_balanced":
            ai1,ai2=v1["case_balanced_ai_cost_per_referral"],v2["case_balanced_ai_cost_per_referral"]
            input1,input2=v1["case_balanced_avg_input_tokens"],v2["case_balanced_avg_input_tokens"]
            output1,output2=v1["case_balanced_avg_output_tokens"],v2["case_balanced_avg_output_tokens"]
            turns1,turns2=v1["case_balanced_avg_turns"],v2["case_balanced_avg_turns"]
        else:
            ai1,ai2=v1["avg_provider_ai_cost_measured"],v2["avg_provider_ai_cost_measured"]
            input1,input2=v1["avg_input_tokens"],v2["avg_input_tokens"]
            output1,output2=v1["avg_output_tokens"],v2["avg_output_tokens"]
            turns1,turns2=v1["avg_turns"],v2["avg_turns"]
        invalid1,invalid2=v1[f"{view}_invalid_output_rate"],v2[f"{view}_invalid_output_rate"]
        out.append({
            "weighting_view": view, "model": v1["model"], "matched_case_trial_keys": 52,
            "v1_pass_rate": pass1, "v2_pass_rate": pass2, "delta_pass_rate_pp": (pass2-pass1)*100,
            "v1_invalid_output_rate": invalid1,
            "v2_invalid_output_rate": invalid2,
            "delta_invalid_output_rate_pp": (invalid2-invalid1)*100,
            "v1_avg_input_tokens": input1, "v2_avg_input_tokens": input2,
            "delta_input_tokens": input2-input1,
            "v1_avg_output_tokens": output1, "v2_avg_output_tokens": output2,
            "delta_output_tokens": output2-output1,
            "v1_avg_turns": turns1, "v2_avg_turns": turns2,
            "delta_turns": turns2-turns1,
            "v1_ai_cost_per_referral": ai1, "v2_ai_cost_per_referral": ai2,
            "delta_ai_cost_per_referral": ai2-ai1,
            "v1_fallback_cost_per_referral": fall1, "v2_fallback_cost_per_referral": fall2,
            "delta_fallback_cost_per_referral": fall2-fall1,
            "v1_total_cost_per_referral": ai1+fall1, "v2_total_cost_per_referral": ai2+fall2,
            "delta_total_cost_per_referral": (ai2+fall2)-(ai1+fall1),
            "v1_monthly_scenario": (ai1+fall1)*MONTHLY_REFERRALS,
            "v2_monthly_scenario": (ai2+fall2)*MONTHLY_REFERRALS,
            "delta_monthly_cost": ((ai2+fall2)-(ai1+fall1))*MONTHLY_REFERRALS,
            "reliability_fallback_effect_per_referral": (pass2-pass1)*float(FAILURE_COST_USD),
            "reliability_fallback_effect_monthly": (pass2-pass1)*float(FAILURE_COST_USD)*MONTHLY_REFERRALS,
            "measurement_status": "MEASURED_MATCHED_PROMPT_CONTROL_PLUS_ASSUMED_FALLBACK",
        })
    return out


def _sensitivity(summary: list[dict]) -> tuple[list[dict], str]:
    formal = [s for s in summary if s["scope"]=="FULL_BATTERY" and s["prompt_version"]=="v2"]
    rows=[]
    for s in formal:
        ai=s["avg_provider_ai_cost_measured"]
        for name,p in sensitivity_rates(s["trial_weighted_pass_rate"]).items():
            rows.append({"experiment_id":s["experiment_id"],"model":s["model"],
                         "scenario":name,"base_trial_weighted_pass_rate":s["trial_weighted_pass_rate"],
                         "scenario_pass_rate":p,"ai_cost_per_referral":ai,
                         "fallback_cost_per_referral":fallback_cost(p),
                         "expected_cost_per_referral":ai+fallback_cost(p),
                         "monthly_variable_cost":monthly_cost(ai,p),
                         "fixed_monthly_cost":0,"measurement_status":"PROVIDER_REPORTED_AI_PLUS_ASSUMED_FALLBACK"})
    unstable=[]; stable=[]
    for i,a in enumerate(formal):
        for b in formal[i+1:]:
            costs_a=[x["expected_cost_per_referral"] for x in rows if x["experiment_id"]==a["experiment_id"]]
            costs_b=[x["expected_cost_per_referral"] for x in rows if x["experiment_id"]==b["experiment_id"]]
            signs={0 if abs(x-y)<1e-12 else (1 if x>y else -1) for x in costs_a for y in costs_b}
            pair=f"{a['experiment_id']} vs {b['experiment_id']}"
            (stable if len(signs)==1 else unstable).append(pair)
    md=("# ±10 percentage-point sensitivity\n\n"
        "LOW/BASE/HIGH alter each formal V2 model's trial-weighted evaluation pass rate by ±0.10 absolute, clamped to [0,1]. "
        "AI execution cost is held at its fully measured D5 provider-cost mean; nurse fallback uses the assignment assumption. "
        "This is a scenario, not a production forecast.\n\n"
        f"Across all independent LOW/BASE/HIGH combinations for each pair, stable pairwise cost orderings: **{len(stable)}**; "
        f"orderings that can change or tie: **{len(unstable)}**. "
        "A changed ordering means no pairwise economic conclusion is robust across the full assumed band.\n\n"
        f"Stable pairs: {', '.join(stable) if stable else 'none'}.\n\n"
        f"Unstable pairs: {', '.join(unstable) if unstable else 'none'}.\n")
    return rows,md


def _break_evens(summary: list[dict]) -> tuple[list[dict], list[dict]]:
    formal=[s for s in summary if s["scope"]=="FULL_BATTERY" and s["prompt_version"]=="v2"]
    pairs=[]
    matrix=[]
    for candidate in formal:
        row={"candidate_experiment_id":candidate["experiment_id"]}
        for benchmark in formal:
            b=benchmark["experiment_id"]
            if candidate is benchmark:
                row[b]=None
                continue
            raw, feasible=break_even(candidate["avg_provider_ai_cost_measured"],benchmark["trial_weighted_total_cost_per_referral"])
            entry={"candidate_experiment_id":candidate["experiment_id"],"benchmark_experiment_id":b,
                   "candidate_ai_cost_per_referral":candidate["avg_provider_ai_cost_measured"],
                   "benchmark_expected_total_cost_per_referral":benchmark["trial_weighted_total_cost_per_referral"],
                   "failure_cost_per_referral":float(FAILURE_COST_USD),
                   "raw_break_even_success_rate":raw,"feasible_break_even_success_rate":feasible,
                   "candidate_measured_trial_weighted_pass_rate":candidate["trial_weighted_pass_rate"],
                   "measured_margin_pp":(candidate["trial_weighted_pass_rate"]-raw)*100,
                   "raw_threshold_feasibility":"WITHIN_0_1" if 0<=raw<=1 else ("BELOW_0" if raw<0 else "ABOVE_1"),
                   "measurement_status":"PROVIDER_REPORTED_AI_PLUS_ASSUMED_FALLBACK"}
            pairs.append(entry)
            row[b]=raw
        matrix.append(row)
    return pairs,matrix


def _pareto(summary: list[dict]) -> list[dict]:
    base=[{"experiment_id":s["experiment_id"],"model":s["model"],"prompt_version":s["prompt_version"],
           "cost":s["trial_weighted_total_cost_per_referral"],"pass_rate":s["trial_weighted_pass_rate"]}
          for s in summary if s["scope"]=="FULL_BATTERY" and s["prompt_version"]=="v2"]
    status=pareto_status(base)
    rows=[]
    for x in base:
        row={"experiment_id":x["experiment_id"],"model":x["model"],"prompt_version":x["prompt_version"],
             "expected_cost_per_referral":x["cost"],"trial_weighted_pass_rate":x["pass_rate"],
             "pareto_status":status[x["experiment_id"]],
             "measurement_status":"PROVIDER_REPORTED_AI_PLUS_ASSUMED_FALLBACK"}
        rows.append(row)
    return rows


def _cost_reconciliation(runs: list[dict], summary: list[dict]) -> list[dict]:
    out=[]
    for s in summary:
        rr=[r for r in runs if r["experiment_id"]==s["experiment_id"]]
        provider=sum(Decimal(str(r["provider_cost_usd"])) for r in rr if r["provider_cost_usd"] is not None)
        listed=sum(Decimal(str(r["recomputed_ai_cost_usd"])) for r in rr if r["recomputed_ai_cost_usd"] is not None)
        out.append({"experiment_id":s["experiment_id"],"model":s["model"],
                    "formal_runs":len(rr),"provider_cost_rows":s["provider_cost_rows"],
                    "provider_reported_scored_spend_usd":str(provider),
                    "config_list_rate_recomputed_spend_usd":str(listed),
                    "provider_minus_recomputed_usd":str(provider-listed),
                    "diagnostic_label":"PROVIDER_VS_LIST_RATE_DIFFERENCE",
                    "recomputed_cost_status":"RECOMPUTED_FROM_D5_CONFIG_LIST_RATE_NOT_INVOICE",
                    "diagnostic_note":"Config list-rate calculation can differ from provider-reported charge, including cached or provider-specific pricing; not a billing-error finding",
                    "missing_provider_cost_rows":len(rr)-s["provider_cost_rows"],
                    "scope":"CURRENT_SELECTED_SCORED_RUN_EVALUATION_ONLY;EXCLUDES_EXTRA_PROVIDER_ERROR"})
    return out


def _common_negative(runs: list[dict], taxonomy: list[dict]) -> list[dict]:
    ids = [x["experiment_id"] for x in inventory() if x["prompt_version"] == "v2"]
    expected = {(f"REF-{case}", trial) for case in range(6060,6066) for trial in range(1,4)}
    categories = {x["run_id"]: x["failure_category"] for x in taxonomy}
    result = []
    for bid in ids:
        group = [r for r in runs if r["experiment_id"] == bid and r["negative_case"]]
        keys = {(r["case_id"],r["trial"]) for r in group}
        if len(group) != 18 or keys != expected:
            raise ValueError(f"Common-negative keys differ: {bid}")
        counts = Counter(categories[r["run_id"]] for r in group)
        result.append({
            "experiment_id":bid, "model":group[0]["model"], "scope":"NEGATIVE_SUBSET_STRESS_TEST_NOT_PRODUCTION",
            "runs":len(group), "cases":len({r["case_id"] for r in group}),
            "passed":sum(r["passed"] for r in group), "pass_rate":sum(r["passed"] for r in group)/len(group),
            "invalid_model_output":sum(r["status"]=="invalid_model_output" for r in group),
            "unsafe_booking_attempts":sum(r["unsafe_book_slot_attempt"] for r in group),
            "provider_spend_usd":float(sum(Decimal(str(r["provider_cost_usd"])) for r in group)),
            "mean_provider_cost_per_run":mean(r["provider_cost_usd"] for r in group),
            "mean_turns":mean(r["turns"] for r in group), "total_turns":sum(r["turns"] for r in group),
            "input_tokens":sum(r["input_tokens"] for r in group),
            "output_tokens":sum(r["output_tokens"] for r in group),
            "cached_input_tokens":sum(r["cached_input_tokens"] or 0 for r in group),
            "reasoning_tokens":sum(r["reasoning_tokens"] or 0 for r in group),
            "provider_cost_coverage":f"{len(group)}/{len(group)}",
            "failure_taxonomy":json.dumps(dict(counts),sort_keys=True),
        })
    return result


def _write_preflight(runs: list[dict], calls: list[dict], batteries: dict, spend: dict) -> None:
    from .config import D6
    pre = D6 / "preflight"
    pre.mkdir(exist_ok=True)
    def write(name, rows):
        fields=list(dict.fromkeys(k for row in rows for k in row))
        with (pre/name).open("w",encoding="utf-8",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=fields)
            writer.writeheader();writer.writerows(rows)
    items=inventory()
    write("experiment_inventory.csv",[
        {"experiment_id":x["experiment_id"],"model_id":x["model_id"],"scope":x["scope"],
         "prompt_version":x["prompt_version"],"family":x["family"],"team_price_tier":x["team_price_tier"],
         "selected_runs":len(batteries[x["experiment_id"]]["runs"]),
         "source":"FROZEN_D5_SELECTED_5PLUS1_INVENTORY_AND_INDEX"}
        for x in items])
    write("data_schema_inventory.csv",[
        {"dataset":name,"rows":len(rows),"columns":len(rows[0]),"field_names":";".join(rows[0])}
        for name,rows in (("selected_runs",runs),("tool_calls",calls))])
    quality=[
        {"check":"selected_scored_runs","observed":len(runs),"expected":278,"status":"PASS" if len(runs)==278 else "FAIL"},
        {"check":"provider_cost_coverage","observed":sum(r["provider_cost_usd"] is not None for r in runs),
         "expected":278,"status":"PASS" if all(r["provider_cost_usd"] is not None for r in runs) else "FAIL"},
        {"check":"selected_scored_spend_usd","observed":spend["selected_scored_run_spend"],
         "expected":2.13502002,"status":"PASS" if abs(spend["selected_scored_run_spend"]-2.13502002)<1e-10 else "FAIL"},
        {"check":"saved_tool_calls","observed":len(calls),"expected":"RECOMPUTED","status":"PASS"},
        {"check":"invalid_output_failures","observed":sum(r["status"]=="invalid_model_output" and not r["passed"] for r in runs),
         "expected":89,"status":"PASS" if sum(r["status"]=="invalid_model_output" and not r["passed"] for r in runs)==89 else "FAIL"},
    ]
    write("data_quality_report.csv",quality)
    if any(x["status"]=="FAIL" for x in quality):
        raise ValueError("Frozen D5 preflight checks failed")
    (pre/"data_quality_report.md").write_text(
        "# Final D5 selection preflight\n\n278 selected scored runs; 278/278 provider charges; "
        f"{len(calls)} saved tool calls recomputed from raw traces. Six experiments: "
        "four full-battery V2, one Frontier negative-only V2, one Qwen V1 control. "
        "All 89 invalid model outputs remain failures. Selection comes from frozen D5 inventory/index and row audit.\n",
        encoding="utf-8")
    write("tool_observation_inventory.csv",[
        {"experiment_id":bid,"tool_calls":sum(c["experiment_id"]==bid for c in calls),
         "saved_payload_count":sum(c["experiment_id"]==bid and c["observation_payload_saved"] for c in calls),
         "measurement_status":"RECOMPUTED_FROM_FROZEN_D5_RAW_TRACES"}
        for bid in batteries])
    (pre/"spend_reconciliation_precheck.md").write_text(
        "# Current selected evaluation spend\n\n"
        f"Scored-run provider spend: USD {spend['selected_scored_run_spend']:.8f} (278/278). "
        f"Extra charged Mistral provider error: USD {spend['extra_charged_mistral_provider_error']:.8f}; "
        f"recorded charges including it: USD {spend['recorded_selected_model_charges_including_error']:.8f}. "
        "Historical account snapshots are a superseded selection/time and are not reconciled here.\n",
        encoding="utf-8")


def run_pipeline() -> dict:
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"charts").mkdir(parents=True,exist_ok=True)
    batteries=load_batteries()
    runs=normalized_runs(batteries)
    if len(runs)!=278 or any(r["backend"]!="live" for r in runs):
        raise ValueError("Final selected live normalization must contain 278 runs")
    registry=load_registry()
    verify_registry(batteries,registry)
    for r in runs:
        r["recomputed_ai_cost_usd"]=recompute_list_rate_cost(r,registry)
        r["recomputed_ai_cost_status"]="RECOMPUTED_FROM_D5_CONFIG_LIST_RATE" if r["recomputed_ai_cost_usd"] is not None else "NOT_AVAILABLE"
    calls=normalized_tool_calls(batteries)
    save_csv("formal_runs_normalized.csv",runs)
    save_csv("tool_calls_normalized.csv",calls)
    taxonomy=taxonomy_rows(runs,batteries)
    save_csv("failure_taxonomy.csv",taxonomy)
    tax_counts=category_counts(taxonomy)
    save_csv("failure_taxonomy_model_counts.csv",[
        {"experiment_id":bid,"failure_category":category,"run_count":count,
         "measurement_status":"MEASURED_FROM_FROZEN_D5"}
        for bid,categories in tax_counts.items() for category,count in sorted(categories.items())])
    safety,safety_lookup=_safety(runs,batteries)
    save_csv("safety_cost_context.csv",safety)
    summary=_summaries(runs,taxonomy,safety_lookup)
    save_csv("model_cost_summary.csv",summary)
    spend,spend_values=_spend(runs,batteries)
    save_csv("evaluation_spend_reconciliation.csv",spend)
    save_csv("cost_reconciliation.csv",_cost_reconciliation(runs,summary))
    common=_common_negative(runs,taxonomy)
    save_csv("common_negative_cost_context.csv",common)
    qwen=_qwen(summary)
    save_csv("qwen_prompt_ablation.csv",qwen)
    sensitivity,sensitivity_md=_sensitivity(summary)
    save_csv("sensitivity_analysis.csv",sensitivity)
    (OUT/"sensitivity_conclusion.md").write_text(sensitivity_md,encoding="utf-8")
    pairs,matrix=_break_evens(summary)
    save_csv("break_even_pairs.csv",pairs)
    save_csv("break_even_matrix.csv",matrix)
    bootstrap=[]
    for s in summary:
        if s["scope"]!="FULL_BATTERY" or s["prompt_version"]!="v2":
            continue
        rr=[r for r in runs if r["experiment_id"]==s["experiment_id"]]
        for metric,values in bootstrap_metrics(rr).items():
            bootstrap.append({"experiment_id":s["experiment_id"],"model":s["model"],
                              "metric":metric,**values,"iterations":BOOTSTRAP_ITERATIONS,"seed":BOOTSTRAP_SEED,
                              "method":"case_id cluster resampling with all within-case trials",
                              "measurement_status":"EVALUATION_SAMPLE_UNCERTAINTY_ONLY"})
    save_csv("bootstrap_uncertainty.csv",bootstrap)
    levers,d2_audit=cost_levers(qwen[0]["delta_pass_rate_pp"]/100,calls)
    save_csv("cost_lever_attribution.csv",levers)
    pareto=_pareto(summary)
    save_csv("pareto_analysis.csv",pareto)
    limits=thresholds(runs)
    anomalies=anomaly_rows(runs,batteries,limits)
    save_csv("cost_anomalies.csv",anomalies)
    governance=proposed_governance(summary,limits)
    save_csv("governance_proposal.csv",governance)
    report={
        "title":"PE6201 A2 Problem B D6 Cost / Agent FinOps",
        "measurement_basis":"FROZEN_FINAL_D5_5PLUS1",
        "business_assumptions":{"monthly_referrals":MONTHLY_REFERRALS,"nurse_hourly_cost_usd":55,
                                "human_minutes_per_failure":10,"failure_cost_usd":float(FAILURE_COST_USD),
                                "value_of_1pp_success_rate_per_month_usd":float(VALUE_OF_ONE_SUCCESS_PP_MONTHLY),
                                "fixed_monthly_cost_baseline_usd":0,
                                "fixed_cost_status":"BASELINE_ASSUMPTION_NOT_MEASURED"},
        "selected_scored_run_count":len(runs),"tool_call_count":len(calls),
        "provider_cost_coverage":"278/278",
        "evaluation_spend":spend_values,
        "model_summary":summary,"common_negative":common,"qwen_prompt_ablation":qwen,
        "sensitivity":sensitivity,"break_even_pairs":pairs,"bootstrap":bootstrap,
        "pareto":pareto,"safety":safety,"d2_control_audit":d2_audit,"cost_levers":levers,
        "anomaly_counts":dict(Counter(flag for row in anomalies for flag in row["anomaly_flags"].split(";") if flag)),
        "governance":governance,
        "limitations":["Evaluation-set rates are not hospital prevalence or a production forecast",
                       "Claude has 18 negative-only runs and no ordinary/full-battery or general-monthly inference",
                       "Four full batteries have 40 cases, six negative and 52 runs, not later expected 40/eight/56",
                       "Claude source-commit full diff unavailable locally",
                       "Fixed deployment cost unmeasured; zero is a baseline assumption",
                       "Historical account snapshot is not reconcilable to this final selected set",
                       "B/D offline lexical units are NOT_PROVIDER_TOKENIZATION; D2 controls are separate",
                       "Team price-tier classification does not assert official exact-model mapping"],
    }
    _write_preflight(runs,calls,batteries,spend_values)
    (OUT/"cost_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    from .report import write_report
    from .charts import make_charts
    write_report(report,sensitivity_md)
    make_charts(report,sensitivity,levers,taxonomy)
    return report
