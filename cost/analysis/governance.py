import math

from .config import MONTHLY_REFERRALS


def proposed_governance(summary_rows: list[dict], limits: dict) -> list[dict]:
    out = []
    for s in summary_rows:
        bid = s["experiment_id"]
        lim = limits[bid]
        out.append({
            "experiment_id": bid, "model": s["model"], "scope": s["scope"],
            "measurement_status": "ACTUAL_STEP_CAP_PLUS_PROPOSED_MONITORING",
            "monitor_only": True,
            "actual_agent_step_cap": 8,
            "actual_agent_step_cap_evidence": "referral-flow-agent/config/__init__.py RunConfig.max_turns; guardrails/core.py checks turn limit; frozen D5 config max_turns=8",
            "proposed_turn_alert": min(8,max(1,math.ceil(lim["turns"] * 1.25))),
            "max_input_tokens_per_run": math.ceil(lim["input_tokens"] * 1.25 / 1000) * 1000,
            "max_output_tokens_per_run": math.ceil(lim["output_tokens"] * 1.25 / 100) * 100,
            "warning_cost_per_run_usd": lim["provider_cost_usd"],
            "warning_cost_status": "PROPOSED_MONITOR_ONLY_BASED_ON_EVALUATION_P95",
            "evaluation_budget_ceiling": "D5_RUNNER_CLI_PER_BATTERY_ONLY_NOT_AGENT_PRODUCTION_CONTROL",
            "monthly_workload_scenario_referrals": MONTHLY_REFERRALS,
            "monthly_per_user_limit": None,
            "monthly_per_user_limit_status": "NOT_IMPLEMENTED;PROPOSED_POLICY_REQUIRES_USER_ALLOCATION",
            "action_deduplication": "IMPLEMENTED_BOOKING_GATE_CONTEXT",
            "autonomy_gate": "CONFIRM_IN_FROZEN_D5_RUNS",
            "policy_note": "Observed step cap is 8; token/turn/cost alerts use within-model evaluation p95 plus documented 25% headroom where applicable. Alert only; no new cap was retroactively applied. 4000 referrals is workload volume, not a per-user limit.",
        })
    return out
