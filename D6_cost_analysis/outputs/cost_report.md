# D6 cost analysis — Problem B

## Scope and business model

Frozen final D5 contains **278 scored live runs** with **278/278 provider-cost coverage**: four 52-run full-battery V2 models, Claude Opus 5 on 18 negative-only trials, and a 52-run Qwen V1 control. Full batteries have 40 cases (34 ordinary once; six negative three times). No 56-run result was synthesized. The five V2 models span five families and two **team-classified price tiers**: GPT, Qwen, Mistral and Gemini are lower-price; Claude is Frontier. This is not an official exact-model-to-tier mapping.

For the four full-battery V2 models only, the scenario uses 4,000 referrals/month, nurse time of 10 minutes/failure, and USD 55/hour. Failure cost is USD 9.1666666667. AI variable cost/referral is mean provider-recorded run charge. Fallback/referral is `(1 - evaluation pass rate) × failure cost`. Monthly scenario is `4,000 × (AI + fallback) + fixed monthly cost`. Fixed deployment cost is **USD 0 solely as a baseline assumption; it was not measured**. Evaluation-rate scenarios are **not hospital forecasts**.

## Full-battery cost-to-serve

| Full-battery V2 | Pass | Case-balanced pass | AI/referral USD | Fallback/referral USD | Total/referral USD | Monthly 4,000 USD | Case-balanced monthly USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| openai/gpt-4o-mini | 17/52 = 32.69% | 19.17% | 0.00120000 | 6.169872 | 6.171072 | 24684.29 | 29644.08 |
| qwen/qwen3-30b-a3b-instruct-2507 | 28/52 = 53.85% | 60.00% | 0.00146558 | 4.230769 | 4.232235 | 16928.94 | 14672.84 |
| mistralai/mistral-small-3.2-24b-instruct | 37/52 = 71.15% | 77.50% | 0.00194501 | 2.644231 | 2.646176 | 10584.70 | 8258.43 |
| google/gemini-2.5-flash | 39/52 = 75.00% | 77.50% | 0.00348414 | 2.291667 | 2.295151 | 9180.60 | 8266.09 |

Case-balanced means first average trials within each case, then give each of 40 cases equal weight. This applies independently to pass, AI cost, tokens and turns. Invalid outputs remain failures: GPT 35/52, Qwen 14/52, Mistral 0/52, Gemini 6/52.

## Claude and matched five-model negative subset

Claude has **10/18 = 55.56%** negative-trial passes, 8/18 invalid outputs, zero unsafe booking attempts, 272,906 input, 11,195 output, 0 cached input and 502 reasoning tokens. Provider spend is USD 1.644405, or USD 0.09135583/run (18/18 coverage). **Overall/full-battery pass, general monthly cost, general sensitivity, break-even and production Pareto are N/A — NEGATIVE_ONLY_SCOPE.** Section 7 permits a Frontier negative-only comparison.

Exactly REF-6060 through REF-6065, three trials each, are common to five V2 models. **NEGATIVE_SUBSET_STRESS_TEST_NOT_PRODUCTION**; no 4,000-referral extrapolation:

| Common 18-trial V2 subset | Pass | Invalid | Unsafe book attempts | Provider spend USD | Mean AI/run USD | Mean turns | Input/output tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| openai/gpt-4o-mini | 14/18 = 77.78% | 4/18 | 0 | 0.01579530 | 0.00087752 | 1.94 | 183174/2484 |
| qwen/qwen3-30b-a3b-instruct-2507 | 6/18 = 33.33% | 2/18 | 7 | 0.02170581 | 0.00120588 | 3.06 | 258668/5641 |
| mistralai/mistral-small-3.2-24b-instruct | 9/18 = 50.00% | 0/18 | 4 | 0.02530985 | 0.00140610 | 2.67 | 257353/5748 |
| google/gemini-2.5-flash | 12/18 = 66.67% | 6/18 | 0 | 0.03037140 | 0.00168730 | 2.00 | 233859/4545 |
| anthropic/claude-opus-5 | 10/18 = 55.56% | 8/18 | 0 | 1.64440500 | 0.09135583 | 1.39 | 272906/11195 |

Per-run failure taxonomy is in `failure_taxonomy.csv`. Unsafe counts are attempted `book_slot` calls on negative cases, not necessarily completed bookings. Safety is not converted into an invented monetary penalty.

## Qwen matched prompt control

V1 is **20/52 = 38.46%**; V2 is **28/52 = 53.85%** on identical keys. Improvement is **+15.38 pp**. Invalid outputs change 26/52 → 14/52. AI cost/referral changes by USD +0.00012541. Success-only assumed fallback changes by USD -1.410256/referral or USD -5641.03/month. Full monthly difference including AI cost is USD -5640.52. Case-balanced pass change is +20.00 pp and monthly difference USD -7332.76.

## Evaluation spend and Section 7

Selected **scored-run** spend is **USD 2.13502002** (278/278). The extra charged Mistral provider-error attempt is **USD 0.00031845**, outside the scored denominator. Recorded selected-model charges including it are **USD 2.13533847**. Historical account increment USD 0.653968992 and residual USD 0.018762122 belong to a superseded selection/time; neither is reconciled to or allocated within the final set.

The local official brief Section 7 (PDF p.16–17) states a **USD 10 personal key for the whole course**, a 56-run per-member/model illustration of about **USD 0.31 cheap / 3.15 mid / 15.74 Frontier**, a USD 3/member estimated-spend warning, and the Frontier negative-only exception. The latest user-supplied update gives **USD 0.27 / 2.76 / 13.78**, but its matching revised official PDF is not locally available; these are therefore **user-supplied updated-reference figures, not independently verified from the local PDF**. Neither reference set is the measured mixed-scope selected spend. No authoritative local evidence establishes USD 2 as an overall/team/current assignment cap, so no such compliance percentage is computed.

## Sensitivity, break-even, uncertainty and Pareto

Only the four full-battery V2 models enter general ±10 **percentage-point** sensitivity. AI cost is fixed and success is clamped to [0,1]. Pairwise break-even uses `p_BE = 1 - (benchmark expected total - candidate AI cost) / failure cost`; raw and feasible-clamped thresholds are retained. Case-cluster bootstrap resamples case IDs with all within-case trials (5,000 iterations; seed 6201). These are **EVALUATION-SAMPLE UNCERTAINTY ONLY**, not hospital-prevalence intervals.

| Model | Median USD | 2.5% USD | 97.5% USD |
| --- | --- | --- | --- |
| openai/gpt-4o-mini | 24715.72 | 18338.16 | 31671.23 |
| qwen/qwen3-30b-a3b-instruct-2507 | 16872.62 | 10191.11 | 23227.78 |
| mistralai/mistral-small-3.2-24b-instruct | 10274.62 | 4174.92 | 17076.32 |
| google/gemini-2.5-flash | 8842.36 | 3680.42 | 15290.25 |

The four-model cost/pass Pareto labels are **PARETO_EFFICIENT** and **DOMINATED**, distinct from price tiers. Safety stays separate.

## B / T / D / S and cost governance

B tool-block and D observation-size evidence uses offline lexical reference units: **NOT_PROVIDER_TOKENIZATION**. Descriptor and return shape changed together, so isolated B/D dollar effects are **NOT_IDENTIFIABLE_CAUSALLY**. T is a separate matched D2 sequential/parallel control, not a D5 battery effect. S is the matched Qwen prompt difference, with assumption-based fallback translation, not measured nurse expenditure.

The Agent implements an 8-turn cap and confirm/booking gate. The D5 runner's per-battery CLI budget is not a production agent budget. p95-based token/cost alerts are **PROPOSED / MONITOR-ONLY**, not retroactive controls. A monthly per-user limit is not implemented or quantified; it requires an allocation policy. The 4,000 referrals are a workload scenario, **not** a per-user limit.

## Limitations

Claude's source commit cannot be fully diffed locally. Four full batteries have 52 runs, below the later 40-case/eight-negative/56-run shape. Historical account snapshots do not reconcile to the current selection. Evaluation rates are not hospital prevalence; fixed deployment cost is unmeasured. All calculations use saved local evidence; no LLM, provider or external API was called.
