# D6 Cost / Agent FinOps

Offline PE6201 Assignment 2 Problem B analysis built from the **frozen final D5 5+1 package**. The current selected set is four 52-run V2 full batteries, an 18-run Claude Frontier negative-only V2 set, and a 52-run Qwen V1 prompt control: **278 scored runs, 278/278 measured provider charges**. D6 does not call a model or change D5 evidence.

## Current deliverables

- `results/d6/cost_report.md` and `.json`: interpretation and machine-readable results.
- `results/d6/formal_runs_normalized.csv`, `model_cost_summary.csv`, `common_negative_cost_context.csv`, `evaluation_spend_reconciliation.csv`: primary audit tables.
- `results/d6/qwen_prompt_ablation.csv`, `sensitivity_analysis.csv`, `break_even_matrix.csv`, `bootstrap_uncertainty.csv`, `pareto_analysis.csv`: economic analyses. General 4,000-referral scenarios use **only the four full-battery V2 models**.
- `results/d6/cost_lever_attribution.csv`, `safety_cost_context.csv`, `governance_proposal.csv`, and `charts/`: engineering, safety, governance, and presentation views.
- `doc/PE6201_D6_Cost_Analysis_Teacher_Submission_FIXED.xlsx`: teacher-facing 11-sheet workbook.
- `results/d6/FINAL_QA_REVIEW.md`: provenance, interpretation limits, tests, and release status.

The authoritative input is `results/d5/`, together with `doc/D5_FINAL_QA.md` and `doc/D5_SCORING_NORMALIZATION_AUDIT.md`. The repository's historical `results/live/` is consulted only for separate D2/guardrail context, not as a replacement for selected D5 results. The D5 selected-model index defines the six experiments. Claude has no overall pass rate or general-population monthly projection; the five-model common-negative comparison is an 18-trial stress test, not production.

## Offline reproduction

From the `referral-flow-agent` repository root, with Python containing NumPy, Pillow and openpyxl:

```powershell
python -B -m unittest tests.test_cost_analysis -v
python -B -m cost.second_pass_qa
```

These are read-only checks of the copied freeze. To regenerate outputs intentionally, run `python -B -m cost.run_analysis`, then `node cost/build_teacher_workbook.mjs` with `@oai/artifact-tool` available locally, and repeat the checks. No external API is needed.

The historical paths and pre-integration test commands in `results/d6/FINAL_QA_REVIEW.md` record the original freeze; integration moved the deliverables without changing their analytical values.

## Measurement boundaries

Selected scored-run provider spend is **USD 2.13502002**. A separately charged Mistral provider-error attempt is **USD 0.00031845**; recorded charges including it are **USD 2.13533847**. Historical account snapshots belong to a superseded selection/time and are not reconciled to this total. All current selected scored runs have measured provider cost; there is no active missing-cost imputation.

The Problem B scenario assumes 4,000 referrals/month, USD 55/hour and 10 minutes of human fallback per failure. Fixed deployment cost is USD 0 **only as an unmeasured baseline assumption**. Trial-weighted economics and equally case-balanced economics are reported separately. Evaluation success rates are not hospital prevalence. GPT, Qwen, Mistral and Gemini are the team's lower-price tier; Claude is the team-selected Frontier tier under the Section 7 negative-only exception. An official exact-ID-to-tier mapping is not asserted.

The seven superseded Llama-era Phase A/earlier-output files were removed after explicit user authorization. Their exact paths, pre-removal SHA-256 hashes, reasons, and classification are preserved in `results/d6/FINAL_QA_REVIEW.md`.
