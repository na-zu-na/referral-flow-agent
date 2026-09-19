import json
import sys
from collections import defaultdict
from statistics import mean

from .config import FAILURE_COST_USD, MONTHLY_REFERRALS, REPO
from .loaders import d2_live
from .normalization import offline_lexical_unit_count


def _variant_stats(rows: list[dict], variant: str) -> dict:
    subset = [r for r in rows if r["variant"] == variant]
    return {
        "runs": len(subset), "pass_rate": mean(bool(r["passed"]) for r in subset),
        "turns": mean(r["turns"] for r in subset),
        "input_tokens": mean(r["tokens_in"] for r in subset),
        "output_tokens": mean(r["tokens_out"] for r in subset),
        "ai_cost": mean(r["cost_usd"] for r in subset),
        "observation_local": mean(o["return_tokens_estimated_chars_div_4"]
                                  for r in subset for o in r.get("observations", [])),
    }


def d2_control_audit(rows: list[dict]) -> dict:
    variants = defaultdict(list)
    for r in rows:
        variants[r["variant"]].append(r)
    keys = [{(r["case_id"], r["trial"]) for r in group} for group in variants.values()]
    models = {r["model"] for r in rows}
    return {
        "same_case_trial_keys": all(x == keys[0] for x in keys),
        "models": sorted(models),
        "variant_count": len(variants),
        "runs_per_variant": {k: len(v) for k, v in variants.items()},
        "prompt_version": "v2 by current RunConfig default; historical value not stored in compact D2 rows",
        "source_commit": "NOT_RECORDED_IN_D2_OUTPUT",
        "execution_modes": {k: sorted({r["call_mode"] for r in v}) for k, v in variants.items()},
        "descriptor_versions": {k: sorted({r["descriptor_version"] for r in v}) for k, v in variants.items()},
    }


def cost_levers(qwen_delta_pass_rate: float, d5_tools: list[dict]) -> tuple[list[dict], dict]:
    d2 = d2_live()
    audit = d2_control_audit(d2)
    if not audit["same_case_trial_keys"] or audit["variant_count"] != 3:
        raise ValueError("D2 controls not comparable within D2")
    v1 = _variant_stats(d2, "descriptor_v1_parallel")
    v2 = _variant_stats(d2, "descriptor_v2_parallel")
    seq = _variant_stats(d2, "callmode_v2_sequential")
    sys.path.insert(0, str(REPO))
    from tools import get_descriptors  # noqa: E402; read-only local source.
    from prompt import build_system_prompt  # noqa: E402
    def desc_text(version):
        values = get_descriptors(version)
        return json.dumps([values[n] for n in sorted(values)], indent=2, sort_keys=True)
    b1 = offline_lexical_unit_count(desc_text("v1"))
    b2 = offline_lexical_unit_count(desc_text("v2"))
    p1 = build_system_prompt("v1", "parallel", "v2")
    p2 = build_system_prompt("v2", "parallel", "v2")
    d5_obs = [t["observation_offline_lexical_units_recomputed"] for t in d5_tools if t["observation_offline_lexical_units_recomputed"] is not None]
    common = {
        "source": "D2 live GPT-4o-mini control; separate from final selected D5 evaluation set",
        "case_set_comparability": "D2 variants matched within D2; D2 cases differ from D5 formal cases",
        "model": "openai/gpt-4o-mini",
        "prompt_version": "v2 by current RunConfig default; not recorded in D2 compact rows",
        "source_commit": "NOT_RECORDED_IN_D2_OUTPUT",
        "reference_segmentation_method": "offline Unicode regex word/punctuation segmentation",
        "provider_tokenization_status": "NOT_PROVIDER_TOKENIZATION",
    }
    rows = [
        {"lever": "B_TOOL_BLOCK", "measurement_status": "RECOMPUTED", **common,
         "economic_effect_status": "NOT_IDENTIFIABLE_CAUSALLY",
         "before_variant": "descriptor_v1_parallel", "after_variant": "descriptor_v2_parallel",
         "before_descriptor_version": "v1", "after_descriptor_version": "v2",
         "before_execution_mode": "parallel", "after_execution_mode": "parallel",
         "before_tool_block_offline_lexical_units": b1, "after_tool_block_offline_lexical_units": b2,
         "before_full_prompt_offline_lexical_units": offline_lexical_unit_count(p1),
         "after_full_prompt_offline_lexical_units": offline_lexical_unit_count(p2),
         "before_observed_ai_cost": v1["ai_cost"], "after_observed_ai_cost": v2["ai_cost"],
         "causal_cost_status": "NOT_IDENTIFIABLE_CAUSALLY",
         "reason": "D2 descriptor version changes tool block and returned observation shape together; no B-only dollar attribution."},
        {"lever": "T_TURN_COUNT", "measurement_status": "MEASURED", **common,
         "economic_effect_status": "MEASURED",
         "before_variant": "callmode_v2_sequential", "after_variant": "descriptor_v2_parallel",
         "before_descriptor_version": "v2", "after_descriptor_version": "v2",
         "before_execution_mode": "sequential", "after_execution_mode": "parallel",
         "before_turns": seq["turns"], "after_turns": v2["turns"],
         "before_input_tokens": seq["input_tokens"], "after_input_tokens": v2["input_tokens"],
         "before_output_tokens": seq["output_tokens"], "after_output_tokens": v2["output_tokens"],
         "before_observed_ai_cost": seq["ai_cost"], "after_observed_ai_cost": v2["ai_cost"],
         "observed_ai_cost_delta_per_run": v2["ai_cost"]-seq["ai_cost"],
         "before_pass_rate": seq["pass_rate"], "after_pass_rate": v2["pass_rate"],
         "fallback_cost_effect_per_referral": -(v2["pass_rate"]-seq["pass_rate"])*float(FAILURE_COST_USD),
         "fallback_cost_effect_monthly": -(v2["pass_rate"]-seq["pass_rate"])*float(FAILURE_COST_USD)*MONTHLY_REFERRALS,
         "total_scenario_delta_per_referral": (v2["ai_cost"]-seq["ai_cost"])-(v2["pass_rate"]-seq["pass_rate"])*float(FAILURE_COST_USD),
         "fallback_translation_status": "ESTIMATED_ASSIGNMENT_ASSUMPTION_ON_D2_EVAL_RATE",
         "causal_cost_status": "MEASURED_WITHIN_D2_CONTROL",
         "reason": "Same D2 case/trial keys, model and v2 descriptor; call mode differs. D2 compact output lacks commit/provenance and is not D5."},
        {"lever": "D_OBSERVATION_SIZE", "measurement_status": "RECOMPUTED", **common,
         "economic_effect_status": "NOT_IDENTIFIABLE_CAUSALLY",
         "before_variant": "descriptor_v1_parallel", "after_variant": "descriptor_v2_parallel",
         "before_descriptor_version": "v1", "after_descriptor_version": "v2",
         "before_execution_mode": "parallel", "after_execution_mode": "parallel",
         "before_observation_local_estimate": v1["observation_local"],
         "after_observation_local_estimate": v2["observation_local"],
         "d5_saved_payload_mean_offline_lexical_units": mean(d5_obs),
         "causal_cost_status": "NOT_IDENTIFIABLE_CAUSALLY",
         "reason": "D2 compact observations lack payloads and v1/v2 changes descriptor plus return shape; D5 has only descriptor v2."},
        {"lever": "S_SUCCESS_RATE", "measurement_status": "ESTIMATED", **common,
         "source": "D5 Qwen V1/V2 matched formal prompt control",
         "case_set_comparability": "same 52 D5 case/trial keys",
         "source_commit": "3d842b705afb58610a781b2351ddc27d3d9ccc0b",
         "economic_effect_status": "ESTIMATED",
         "before_variant": "qwen3_30b_v1", "after_variant": "qwen3_30b_v2",
         "model": "qwen/qwen3-30b-a3b-instruct-2507",
         "prompt_version": "v1 to v2; D5 formal prompt control",
         "before_descriptor_version": "v2", "after_descriptor_version": "v2",
         "before_execution_mode": "parallel", "after_execution_mode": "parallel",
         "delta_pass_rate_pp": qwen_delta_pass_rate * 100,
         "fallback_cost_effect_per_referral": -qwen_delta_pass_rate * float(FAILURE_COST_USD),
         "fallback_cost_effect_monthly": -qwen_delta_pass_rate * float(FAILURE_COST_USD) * MONTHLY_REFERRALS,
         "fallback_translation_status": "ESTIMATED_ASSIGNMENT_ASSUMPTION_ON_D5_QWEN_CONTROL",
         "causal_cost_status": "ASSUMPTION_BASED_TRANSLATION_OF_CONTROLLED_PROMPT_DIFFERENCE",
         "reason": "Qwen matched prompt control; nurse fallback is assignment assumption, not D5 measured spend."},
    ]
    return rows, audit
