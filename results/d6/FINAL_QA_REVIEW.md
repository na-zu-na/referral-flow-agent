# Final D6 QA — frozen D5 5+1 rebuild

## Release result

**Core calculation and CSV/Markdown/XLSX second-pass consistency: PASS. Package freeze: READY.** After explicit user authorization, the seven superseded Llama-era Phase A/output files were hashed, recorded below, and removed without relocation inside D6. Release QA found zero retained legacy files. No external API, model or provider was called. D5 and Agent business logic were not modified.

## Frozen provenance and selection

The primary source is `results/d5/`: `SELECTED_5PLUS1_INVENTORY.csv`; `live/SELECTED_FINAL_INDEX.json`; and each selected experiment's `scored_reviewed/runs.csv`, `trials.csv`, `tool_calls.csv`, `raw_checkpoint.jsonl`, `battery_manifest.json`, and any `provider_errors.jsonl`. Score normalization is joined from `results/d5/D5_NORMALIZED_SCORE_CHANGES.csv`; `doc/D5_FINAL_QA.md`, `doc/D5_SCORING_NORMALIZATION_AUDIT.md`, `results/d5/D5_COMPARISON.md` and `results/d5/D5_COST_RECONCILIATION.md` document the freeze. The historical `results/live/` archive is **not** substituted as primary evidence. Its D2 compact control is separate engineering evidence only.

The following SHA-256 values are the current D5 baseline checked by D6. The D5 QA hash was refreshed after the operator-responsibility metadata correction; the other six analytical evidence files are unchanged. D5 test discovery passes 5/5.

| D5 file (relative to workspace) | Current SHA-256 baseline |
| --- | --- |
| `doc/D5_FINAL_QA.md` | `3D15ECD7B9AE8612240428D3E07293BCD4EDB0C5FC7610B4922EBB00FB403403` |
| `results/d5/D5_NORMALIZED_SCORE_CHANGES.csv` | `B747D93283CB7394AA8F1E72CB620AD29CE43ABC962568EB24A94AB7A3E5086F` |
| `doc/D5_SCORING_NORMALIZATION_AUDIT.md` | `378E8B5B1F9E15451DEEB7A892E86FA74F0197FE68D1764FF8D2AFC20C996EBC` |
| `results/d5/SELECTED_5PLUS1_INVENTORY.csv` | `824B0A69E15FD01E3D6EF7D4BE44164490D52CB69A907ACEA219E3CF97513E2F` |
| `results/d5/live/SELECTED_FINAL_INDEX.json` | `51070EC767DCBC94124CD3E90917DFD03E5F10475B3A5E34C918DB4AEE4783C3` |
| `results/d5/D5_COMPARISON.md` | `64AC68F4D0827DA61B59DC9207B2BB403740E8C4DFB963A828CEA2B359A67C4E` |
| `results/d5/D5_COST_RECONCILIATION.md` | `7A4AB7DA3C2C2B3A28F8DD1B91569D0FE5DF57C46BE9ED697C1F8DB511716B9A` |

Final 5+1: four 52-run full-battery V2 models (GPT-4o-mini, Qwen 3 30B, Mistral Small 3.2, Gemini 2.5 Flash); Claude Opus 5 V2 on 18 negative-only trials; and Qwen V1 on 52 matched prompt-control trials. Thus **4 × 52 + 18 + 52 = 278** selected scored rows, **278/278** measured provider charges, zero score-label changes, and 89 invalid model outputs. The five V2 families are OpenAI, Qwen, Mistral, Google and Anthropic. GPT/Qwen/Mistral/Gemini are the team's lower-price tier and Claude the team-selected Frontier tier: two tiers. No official course mapping of these exact model IDs is claimed. Claude used the Section 7 Frontier negative-only exception.

Current operator responsibility is FAN YANXI — GPT-4o-mini V2; HOU YUXUAN — Qwen 3 30B V2; LIN SIYUAN — Mistral Small 3.2 V2; WEN HAO — Gemini 2.5 Flash V2; CHEN CHANG — Claude Opus 5 V2; and ZHOU YU — Qwen V1 prompt control. This metadata correction does not alter any trace, score, token, provider charge, or D6 economic output.

## Economics and quality

The assignment scenario uses 4,000 referrals/month, USD 55/hour and 10 fallback minutes per failed referral; `F = 55 × 10 / 60 = USD 9.1666666667`. Expected total/referral is provider AI cost plus `(1 − success rate) × F`; monthly is 4,000 times this plus fixed deployment cost. Fixed USD 0 is an **unmeasured baseline assumption**, not measured deployment spending. Evaluation-set rates are not hospital prevalence.

| Full-battery V2 | Pass | Invalid | Unsafe negative booking attempts | Trial-weighted monthly USD | Case-balanced monthly USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| GPT-4o-mini | 17/52 | 35/52 | 0 | 24,684.29 | 29,644.075883888887 |
| Qwen 3 30B | 28/52 | 14/52 | 7 | 16,928.94 | 14,672.840641666666 |
| Mistral Small 3.2 | 37/52 | 0/52 | 4 | 10,584.70 | 8,258.426726666665 |
| Gemini 2.5 Flash | 39/52 | 6/52 | 0 | 9,180.60 | 8,266.09277 |

The case-balanced calculation first averages all measured rows **within each case ID**, then equally averages the 40 case means. It is applied separately to pass rate, AI charge, tokens, turns and resulting fallback/total/monthly economics; it is not a simple 52-row mean. Four batteries have 40 unique cases (34 ordinary once, six negative three times), not the later expected 40-case/eight-negative/56-run shape. No trials were synthesized.

Claude: six negative cases × three trials = **10/18 pass**, **8/18 invalid**, zero unsafe negative booking attempts; 272,906 input, 11,195 output, zero cached input and 502 reasoning tokens; **USD 1.644405** provider spend, **USD 0.0913558333/run**, coverage 18/18. Its overall/full-battery pass and general monthly, sensitivity, break-even and production Pareto remain **N/A — NEGATIVE_ONLY_SCOPE**. A complete source-tree diff against Claude's recorded commit remains unavailable locally; matching saved payloads/configuration does not remove this provenance limitation.

The only five-model direct comparison is **NEGATIVE_SUBSET_STRESS_TEST_NOT_PRODUCTION** on identical `(case_id, trial)` keys for REF-6060 through REF-6065, three trials each:

| V2 model | Pass / 18 | Invalid / 18 | Unsafe attempts |
| --- | ---: | ---: | ---: |
| GPT | 14/18 | 4/18 | 0 |
| Qwen | 6/18 | 2/18 | 7 |
| Mistral | 9/18 | 0/18 | 4 |
| Gemini | 12/18 | 6/18 | 0 |
| Claude | 10/18 | 8/18 | 0 |

Qwen's matched V1 → V2 control is **20/52 → 28/52**, a **+15.38 percentage-point** trial-weighted success change (case-balanced +20.00 pp). The AI execution-cost change is +USD 0.00012541/referral. Under the fallback assumption, success alone changes fallback by −USD 1.410256/referral or −USD 5,641.03/month; the full monthly difference including AI cost is −USD 5,640.52. These are scenario translations, not observed nurse spending.

## Spend, Section 7 and decision analysis

Selected **scored-run** provider spend is **USD 2.13502002**. The extra charged Mistral provider-error call is **USD 0.00031845**, **not** another scored trial. Recorded selected-model charges including the error are **USD 2.13533847**. Historical account increment USD 0.653968992 and unattributed residual USD 0.018762122 are from a superseded selection/time; they cannot be reconciled or allocated to the current 5+1. Provider-vs-list-rate difference is a diagnostic, not proof of billing error.

The locally available official assignment PDF Section 7 describes a USD 10 **personal key for the whole course**, a 56-run per-member/model illustration of about USD 0.31 cheap / 3.15 mid / 15.74 Frontier, an estimated-spend warning above USD 3/member, and the Frontier negative-only exception. A latest user-supplied update gives USD 0.27 / 2.76 / 13.78 for those reference batteries, but its matching revised official PDF was not locally available, so those revised figures are marked **user-supplied, not independently verified**. Neither reference is the measured final mixed-scope spend; no USD 2 overall assignment cap is asserted.

General sensitivity moves success by **±10 percentage points**, clamps to [0,1], holds AI cost fixed, and includes only the four full batteries. Pairwise break-even uses `p_BE = 1 − (benchmark total cost − candidate AI cost) / failure cost` for those same four. Uncertainty is a 5,000-iteration, seed-6201 **case-cluster bootstrap**, labelled **EVALUATION-SAMPLE UNCERTAINTY ONLY**. Cost/pass Pareto status uses `PARETO_EFFICIENT` or `DOMINATED`; `PRICE_TIER` is a separate concept. Unsafe actions remain a separate safety dimension, with no invented monetary penalty.

## B/T/D/S and governance

- **B tool block / D observation size:** saved D2/tool-descriptor evidence uses reproducible offline lexical reference units, **NOT_PROVIDER_TOKENIZATION**. Descriptor and return shape changed together; separate causal dollar effects are **NOT_IDENTIFIABLE_CAUSALLY**. D2 compact output lacks full historical provenance and is not pooled with D5.
- **T turns:** matched D2 sequential/parallel comparison is a separate control, not a D5 battery result; its observed turn/token/cost differences are reported only within that design.
- **S success:** matched D5 Qwen prompt control above. The fallback translation is assumption-based; its success-only effect is separated from the full AI-plus-fallback difference.
- **Three requested caps:** the Agent has an actual **8-turn step cap** and booking/confirm guardrails. The D5 runner's per-battery CLI budget is not a production agent budget ceiling. Token/turn/cost thresholds are **PROPOSED / MONITOR-ONLY**; no production budget ceiling or monthly per-user limit is evidenced as implemented. A per-user allocation policy is still required. The 4,000-referral workload scenario is not a per-user limit. Action de-duplication and abnormal usage monitoring are documented as governance context.

## Second-pass tests and integrity

All current integration checks were local; no model, OpenRouter, LLM/provider or other external API call was made.

| Suite / working directory | Exact command | Result |
| --- | --- | --- |
| D6 integrated cost tests / repository root | `.venv\Scripts\python.exe -B -m unittest tests.test_cost_analysis -v` | 11/11 pass |
| D5 integrated final tests / repository root | `.venv\Scripts\python.exe -B -m unittest tests.test_d5_final -v` | 5/5 pass |
| Complete repository suite / repository root | `.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -q` | 116/116 pass |
| Independent second pass / repository root | `.venv\Scripts\python.exe -B -m cost.second_pass_qa` | 2,169 calculation/integrity assertions pass; 0 release blockers |

The second pass re-read frozen D5 row-level scores, usage and provider charges; compared selected keys and all 18 common negative keys; compared D6 CSV with Markdown and JSON; reopened all 11 XLSX sheets with openpyxl in formula and cached-value modes; checked formula errors, hidden rows, scope, displayed numerators, key values, column width and wrapping. Workbook previews were rendered and visually inspected during the build. After removal, the read-only release QA passed 2,169 assertions and a stale-string sweep of 44 active source/generated/preflight files, with zero retained legacy blockers. The seven files in the disposition table are absent; the audit table itself is historical metadata, not active model logic.

The workbook's Claude spend now writes `1.644405` exactly: an intermediate float-sum string `1.6444050000000001` was found by second-pass QA, fixed with Decimal sum in the D6 generator, and the affected CSV/JSON/Markdown/workbook regenerated before final checks. No raw D5 cost/token field was altered.

## Authorized superseded-file disposition (recorded before deletion)

The user explicitly authorized audit-preserving removal of **only** the seven files below. Each was resolved as a regular file inside `D:\fuckingwork\D6_cost_analysis` and hashed before deletion. This table preserves identity and reason; it is an audit record, not a current selected-model result. Classification for every row is `SUPERSEDED_LLAMA_ERA_D6_ARTIFACT`.

| Full path | SHA-256 before removal | Reason for removal | Classification |
| --- | --- | --- | --- |
| `D:\fuckingwork\D6_cost_analysis\outputs\missing_cost_sensitivity.csv` | `8B454A59B309B7A22FE8836C43368098C6494537C4283D1E34EB9366AA29699B` | Obsolete missing-cost scenarios for an unselected model; current 278/278 cost coverage makes them inapplicable. | `SUPERSEDED_LLAMA_ERA_D6_ARTIFACT` |
| `D:\fuckingwork\D6_cost_analysis\outputs\pareto_frontier.csv` | `5C6350990397EBF80A938D3FD4FACEF7397AB2C61AAFE90EE43EE2A1120B2387` | Superseded cost/quality table includes the unselected model and obsolete Pareto terminology. | `SUPERSEDED_LLAMA_ERA_D6_ARTIFACT` |
| `D:\fuckingwork\D6_cost_analysis\preflight\d6_readiness_matrix.csv` | `8CFB6314FDCDCF5984E1EFFBCC7258A314561BC9E7C8B55A0A1885CE491644F9` | Old readiness counts and model inventory contradict the frozen final 5+1. | `SUPERSEDED_LLAMA_ERA_D6_ARTIFACT` |
| `D:\fuckingwork\D6_cost_analysis\preflight\experiment_integrity.md` | `73DB8B6C7033DA11333BDA24CDB87F5DA789C4636568D68D4F6451E9D3ED291E` | Old experiment-integrity narrative refers to the superseded selection. | `SUPERSEDED_LLAMA_ERA_D6_ARTIFACT` |
| `D:\fuckingwork\D6_cost_analysis\preflight\phase_a_summary.md` | `CC8965D669B13F271610C11C828A79F9419DDC2F8C1C234C4300A2CCD1E71BAB` | Phase A summary predates the frozen final selected set and has obsolete counts. | `SUPERSEDED_LLAMA_ERA_D6_ARTIFACT` |
| `D:\fuckingwork\D6_cost_analysis\preflight\repository_audit.md` | `A96110DBFAC89A65A756958AE4A468BE8A921E513BB50DE9D074FA499A3BB595` | Repository audit narrative uses superseded selected-model evidence. | `SUPERSEDED_LLAMA_ERA_D6_ARTIFACT` |
| `D:\fuckingwork\D6_cost_analysis\preflight\scripts\audit_phase_a.py` | `7CAEB1DDAD539EF3F06029ABDF3A8A4A20C49C0D32125F9960E290F0AE0AD625` | Old audit script hardcodes the superseded model/counts and would regenerate stale conclusions. | `SUPERSEDED_LLAMA_ERA_D6_ARTIFACT` |

## Removal confirmation and changed-file inventory

Automatic command review initially rejected deletion because of audit-evidence risk. The user then explicitly authorized audit-preserving removal of exactly the seven files listed in the disposition table. Their paths and hashes were recorded in this document **before** deletion. Post-deletion checks confirmed all seven absent and no copy moved into the final D6 tree. The removed files were:

1. `outputs/missing_cost_sensitivity.csv`
2. `outputs/pareto_frontier.csv`
3. `preflight/d6_readiness_matrix.csv`
4. `preflight/experiment_integrity.md`
5. `preflight/phase_a_summary.md`
6. `preflight/repository_audit.md`
7. `preflight/scripts/audit_phase_a.py`

The earlier D6 rebuild generated the current analysis outputs and workbook. The later repository integration moved implementation into `cost/`, evidence into `results/d5/` and `results/d6/`, tests into `tests/`, and documentation/workbook into `doc/`. Analytical CSV/JSON/PNG/XLSX values were not regenerated by the layout change. Current D5 baseline hashes match **7/7** and the complete integrated suite passes **116/116**.

The locally unavailable matching Section 7 update PDF remains a **WARN only**; the user-supplied updated reference figures are labelled as unverified from that local official PDF.

**FINAL_STATUS: D6_FREEZE_READY. BLOCKER: 0.** Core calculations, workbook consistency, frozen-source integrity and post-removal release/stale-reference QA all pass.
