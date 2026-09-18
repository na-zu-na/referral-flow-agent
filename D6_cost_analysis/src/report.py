"""Teacher-facing Markdown report from frozen final D5 row-level calculations."""
from .config import OUT


def table(headers, rows):
    return "\n".join(
        ["| "+" | ".join(headers)+" |", "| "+" | ".join("---" for _ in headers)+" |"]
        + ["| "+" | ".join(str(x) for x in row)+" |" for row in rows])


def write_report(report: dict, sensitivity_md: str) -> None:
    summaries=report["model_summary"]
    full=[x for x in summaries if x["scope"]=="FULL_BATTERY" and x["prompt_version"]=="v2"]
    claude=next(x for x in summaries if x["scope"]=="FRONTIER_NEGATIVE_ONLY")
    common=report["common_negative"]
    spend=report["evaluation_spend"]
    qtrial,qcase=report["qwen_prompt_ablation"]
    full_table=table(
        ["Full-battery V2","Pass","Case-balanced pass","AI/referral USD","Fallback/referral USD","Total/referral USD","Monthly 4,000 USD","Case-balanced monthly USD"],
        [[x["model"],f'{x["passed_runs"]}/{x["runs"]} = {x["trial_weighted_pass_rate"]:.2%}',
          f'{x["case_balanced_pass_rate"]:.2%}',f'{x["avg_provider_ai_cost_measured"]:.8f}',
          f'{x["trial_weighted_fallback_cost_per_referral"]:.6f}',
          f'{x["trial_weighted_total_cost_per_referral"]:.6f}',
          f'{x["trial_weighted_monthly_cost"]:.2f}',f'{x["case_balanced_monthly_cost"]:.2f}'] for x in full])
    negative_table=table(
        ["Common 18-trial V2 subset","Pass","Invalid","Unsafe book attempts","Provider spend USD","Mean AI/run USD","Mean turns","Input/output tokens"],
        [[x["model"],f'{x["passed"]}/18 = {x["pass_rate"]:.2%}',f'{x["invalid_model_output"]}/18',
          x["unsafe_booking_attempts"],f'{x["provider_spend_usd"]:.8f}',
          f'{x["mean_provider_cost_per_run"]:.8f}',f'{x["mean_turns"]:.2f}',
          f'{x["input_tokens"]}/{x["output_tokens"]}'] for x in common])
    boot=[x for x in report["bootstrap"] if x["metric"]=="monthly_cost"]
    boot_table=table(["Model","Median USD","2.5% USD","97.5% USD"],
                     [[x["model"],f'{x["median"]:.2f}',f'{x["p2_5"]:.2f}',f'{x["p97_5"]:.2f}'] for x in boot])
    text=f"""# D6 cost analysis — Problem B

## Scope and business model

Frozen final D5 contains **278 scored live runs** with **278/278 provider-cost coverage**: four 52-run full-battery V2 models, Claude Opus 5 on 18 negative-only trials, and a 52-run Qwen V1 control. Full batteries have 40 cases (34 ordinary once; six negative three times). No 56-run result was synthesized. The five V2 models span five families and two **team-classified price tiers**: GPT, Qwen, Mistral and Gemini are lower-price; Claude is Frontier. This is not an official exact-model-to-tier mapping.

For the four full-battery V2 models only, the scenario uses 4,000 referrals/month, nurse time of 10 minutes/failure, and USD 55/hour. Failure cost is USD {report["business_assumptions"]["failure_cost_usd"]:.10f}. AI variable cost/referral is mean provider-recorded run charge. Fallback/referral is `(1 - evaluation pass rate) × failure cost`. Monthly scenario is `4,000 × (AI + fallback) + fixed monthly cost`. Fixed deployment cost is **USD 0 solely as a baseline assumption; it was not measured**. Evaluation-rate scenarios are **not hospital forecasts**.

## Full-battery cost-to-serve

{full_table}

Case-balanced means first average trials within each case, then give each of 40 cases equal weight. This applies independently to pass, AI cost, tokens and turns. Invalid outputs remain failures: GPT 35/52, Qwen 14/52, Mistral 0/52, Gemini 6/52.

## Claude and matched five-model negative subset

Claude has **{claude["passed_runs"]}/18 = {claude["passed_runs"]/18:.2%}** negative-trial passes, {claude["invalid_model_output_count"]}/18 invalid outputs, zero unsafe booking attempts, {claude["total_input_tokens"]:,} input, {claude["total_output_tokens"]:,} output, {claude["total_cached_input_tokens"]} cached input and {claude["total_reasoning_tokens"]} reasoning tokens. Provider spend is USD {claude["provider_spend_usd"]:.6f}, or USD {claude["avg_provider_ai_cost_measured"]:.8f}/run (18/18 coverage). **Overall/full-battery pass, general monthly cost, general sensitivity, break-even and production Pareto are N/A — NEGATIVE_ONLY_SCOPE.** Section 7 permits a Frontier negative-only comparison.

Exactly REF-6060 through REF-6065, three trials each, are common to five V2 models. **NEGATIVE_SUBSET_STRESS_TEST_NOT_PRODUCTION**; no 4,000-referral extrapolation:

{negative_table}

Per-run failure taxonomy is in `failure_taxonomy.csv`. Unsafe counts are attempted `book_slot` calls on negative cases, not necessarily completed bookings. Safety is not converted into an invented monetary penalty.

## Qwen matched prompt control

V1 is **20/52 = {qtrial["v1_pass_rate"]:.2%}**; V2 is **28/52 = {qtrial["v2_pass_rate"]:.2%}** on identical keys. Improvement is **{qtrial["delta_pass_rate_pp"]:+.2f} pp**. Invalid outputs change 26/52 → 14/52. AI cost/referral changes by USD {qtrial["delta_ai_cost_per_referral"]:+.8f}. Success-only assumed fallback changes by USD {-qtrial["reliability_fallback_effect_per_referral"]:+.6f}/referral or USD {-qtrial["reliability_fallback_effect_monthly"]:+.2f}/month. Full monthly difference including AI cost is USD {qtrial["delta_monthly_cost"]:+.2f}. Case-balanced pass change is {qcase["delta_pass_rate_pp"]:+.2f} pp and monthly difference USD {qcase["delta_monthly_cost"]:+.2f}.

## Evaluation spend and Section 7

Selected **scored-run** spend is **USD {spend["selected_scored_run_spend"]:.8f}** (278/278). The extra charged Mistral provider-error attempt is **USD {spend["extra_charged_mistral_provider_error"]:.8f}**, outside the scored denominator. Recorded selected-model charges including it are **USD {spend["recorded_selected_model_charges_including_error"]:.8f}**. Historical account increment USD 0.653968992 and residual USD 0.018762122 belong to a superseded selection/time; neither is reconciled to or allocated within the final set.

The local official brief Section 7 (PDF p.16–17) states a **USD 10 personal key for the whole course**, a 56-run per-member/model illustration of about **USD 0.31 cheap / 3.15 mid / 15.74 Frontier**, a USD 3/member estimated-spend warning, and the Frontier negative-only exception. The latest user-supplied update gives **USD 0.27 / 2.76 / 13.78**, but its matching revised official PDF is not locally available; these are therefore **user-supplied updated-reference figures, not independently verified from the local PDF**. Neither reference set is the measured mixed-scope selected spend. No authoritative local evidence establishes USD 2 as an overall/team/current assignment cap, so no such compliance percentage is computed.

## Sensitivity, break-even, uncertainty and Pareto

Only the four full-battery V2 models enter general ±10 **percentage-point** sensitivity. AI cost is fixed and success is clamped to [0,1]. Pairwise break-even uses `p_BE = 1 - (benchmark expected total - candidate AI cost) / failure cost`; raw and feasible-clamped thresholds are retained. Case-cluster bootstrap resamples case IDs with all within-case trials (5,000 iterations; seed 6201). These are **EVALUATION-SAMPLE UNCERTAINTY ONLY**, not hospital-prevalence intervals.

{boot_table}

The four-model cost/pass Pareto labels are **PARETO_EFFICIENT** and **DOMINATED**, distinct from price tiers. Safety stays separate.

## B / T / D / S and cost governance

B tool-block and D observation-size evidence uses offline lexical reference units: **NOT_PROVIDER_TOKENIZATION**. Descriptor and return shape changed together, so isolated B/D dollar effects are **NOT_IDENTIFIABLE_CAUSALLY**. T is a separate matched D2 sequential/parallel control, not a D5 battery effect. S is the matched Qwen prompt difference, with assumption-based fallback translation, not measured nurse expenditure.

The Agent implements an 8-turn cap and confirm/booking gate. The D5 runner's per-battery CLI budget is not a production agent budget. p95-based token/cost alerts are **PROPOSED / MONITOR-ONLY**, not retroactive controls. A monthly per-user limit is not implemented or quantified; it requires an allocation policy. The 4,000 referrals are a workload scenario, **not** a per-user limit.

## Limitations

Claude's source commit cannot be fully diffed locally. Four full batteries have 52 runs, below the later 40-case/eight-negative/56-run shape. Historical account snapshots do not reconcile to the current selection. Evaluation rates are not hospital prevalence; fixed deployment cost is unmeasured. All calculations use saved local evidence; no LLM, provider or external API was called.
"""
    (OUT/"cost_report.md").write_text(text,encoding="utf-8")
