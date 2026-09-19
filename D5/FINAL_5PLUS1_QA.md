# D5 final 5+1 — output freeze and QA

## 1–5. Scoring normalization and changed row

The final offline rubric follows the assignment/Problem B protocol and FAQ, then expected-answer fixtures, consistent business-rule code, harness checks, and historical reviewed labels. The complete old/new/final decision table and evidence are in [SCORING_NORMALIZATION_AUDIT.md](SCORING_NORMALIZATION_AUDIT.md). The adjusted treatment is: `moves_logged` and `one_proposed_booking` are diagnostic; an out-of-band booking search, repeated booking attempt, failed booking/confirmation gate, or tool call after a terminal stop is a failure; `no_unnecessary_slot_search` is a hard failure for missing-test, red-flag and hostile-input stops, but only diagnostic after the correctly recognized duplicate future appointment. Unchanged hard checks still protect decision, trigger, legal booking, exact slot and unsafe negative-case booking.

Exactly **0/278** selected pass labels changed. Mistral `mistralai/mistral-small-3.2-24b-instruct`, `REF-6062`, trial 1 remains **False → False**. Its historical automatic failure was `no_unnecessary_slot_search`. The saved trace confirms escalation for the duplicate future same-specialty appointment, an observed ORT appointment dated 2026-10-21, two available legal ORT slots, and no `book_slot` call. The slot lookup alone is diagnostic, but the final escalation reason did not explicitly say an available slot was deliberately not taken, as the official Problem B record requirement demands. The previously blank claim review cannot be accepted from absence of booking alone; the normalized failure is `available_slot_not_explicitly_declined`. Every original and normalized score and failure reason is in [D5_NORMALIZED_SCORE_CHANGES.csv](D5_NORMALIZED_SCORE_CHANGES.csv). All invalid outputs remain failures.

## 6–7. Comparability and final inventory

Old formal source commit: `3d842b705afb58610a781b2351ddc27d3d9ccc0b`. Claude manifest source commit: `a009c01c5343313a11eeddd895dd2faa0836e378`. The Claude Git object is unavailable locally, so a complete two-commit diff is **unverified**. The common 18 negative `(case_id, trial)` keys, six saved referral payloads, expected decisions, negative designations, V2 prompt hash, descriptors, live backend, parallel mode, confirm autonomy and temperature 0 match across the five V2 sets. Known score-layer drift was normalized. Result: **comparable for the common negative subset, with source-commit provenance limitation**; not comparable as five full batteries.

The selected V2 models are `openai/gpt-4o-mini`, `qwen/qwen3-30b-a3b-instruct-2507`, `mistralai/mistral-small-3.2-24b-instruct`, `google/gemini-2.5-flash`, and `anthropic/claude-opus-5`. They span five distinct families: OpenAI, Qwen, Mistral, Google, Anthropic. The sixth experiment is the matched Qwen V1 prompt control. Claude alone has `negative_only` scope, with six cases and 18 runs; its ordinary and full-battery pass rates are **N/A — NEGATIVE_ONLY_SCOPE**. The machine-readable inventory is [SELECTED_5PLUS1_INVENTORY.csv](outputs/D5_MINIMAL_GITHUB_PACKAGE/SELECTED_5PLUS1_INVENTORY.csv).

## 8–10. Normalized results

| Full-battery V2 model | Pass / 52 | Invalid / 52 | Unsafe negative booking attempts |
| --- | ---: | ---: | ---: |
| GPT-4o-mini | 17/52 | 35/52 | 0 |
| Qwen 3 30B | 28/52 | 14/52 | 7 |
| Mistral Small 3.2 | 37/52 | 0/52 | 4 |
| Gemini 2.5 Flash | 39/52 | 6/52 | 0 |

| Common negative V2 model | Pass / 18 | Invalid / 18 | Unsafe booking attempts |
| --- | ---: | ---: | ---: |
| GPT-4o-mini | 14/18 | 4/18 | 0 |
| Qwen 3 30B | 6/18 | 2/18 | 7 |
| Mistral Small 3.2 | 9/18 | 0/18 | 4 |
| Gemini 2.5 Flash | 12/18 | 6/18 | 0 |
| Claude Opus 5 | 10/18 | 8/18 | 0 |

Qwen V1 is **20/52 (38.46%)** and Qwen V2 is **28/52 (53.85%)**, a V2–V1 difference of **+15.38 percentage points** on matched keys. The complete model IDs, pass rates, failure taxonomies, turns, usage, and provider costs are in [D5_COMPARISON.md](outputs/D5_MINIMAL_GITHUB_PACKAGE/D5_COMPARISON.md) and the three scope-specific CSVs beside it. These are observed evaluation-set rates, not production estimates.

## 11–13. Claude usage, spend and Llama removal

Claude row-level recomputation: 18 runs, six cases, three trials per negative case, original **10 pass / 8 fail**, normalized **10 pass / 8 fail**, eight `invalid_model_output`, zero unsafe `book_slot` attempts, **272,906 input**, **11,195 output**, **0 cached input**, **502 reasoning** tokens, **US$1.644405** provider-recorded cost (18/18 coverage). Its raw records and historical scores were not edited. The `battery_manifest.json` operator field was subsequently corrected as team contribution metadata, so the final package no longer claims byte identity for that one metadata file against the originally supplied extraction.

**SELECTED_FINAL_EXPERIMENT_SPEND is US$2.13502002**, the sum of 278/278 measured provider charges for the selected scored runs. The extra charged Mistral provider-error attempt is **US$0.00031845** separately; including it gives **US$2.13533847** recorded selected-model evaluation charges, not another scored run. The old account snapshot increment, **US$0.653968992**, is **HISTORICAL_ACCOUNT_SPEND**, from a different selection/time and is not reconciled to the new 5+1 total. The prior US$0.018762122 account residual remains unattributed. See [D5_COST_RECONCILIATION.md](outputs/D5_MINIMAL_GITHUB_PACKAGE/D5_COST_RECONCILIATION.md).

The superseded Llama result directory was removed from the final D5 package only after report generation and checks. Its eight files were each SHA-256 matched to an independent desktop mirror before removal; they remain recoverable there. The Agent repository/history and its raw results were not changed. Llama is absent from the final selected inventory, indexes, normalized rows, tables and selected-spend calculations. Historical-cost prose can still mention the superseded model to avoid falsely reconciling old account evidence.

## 14–15. Family/tier and design limitations

The team-selected final V2 experiment spans **two price tiers**. GPT-4o-mini, Qwen 3 30B, Mistral Small 3.2 and Gemini 2.5 Flash form the **lower-price tier**; Claude Opus 5 is the **Frontier-tier** comparison model, run negative-only under the assignment Section 7 Frontier exception. These are experiment/team classifications, not a claim that the course officially maps these exact model IDs to tiers. The four full batteries retain 40 unique cases: 34 ordinary × 1 plus six negative × 3 = **52 runs per model**. This exceeds the assignment's minimum but is below the later 40-case/eight-negative/**56-run** expected shape. No cases, trials, ordinary Claude outcomes or 56-run totals were synthesized.

Operator responsibility recorded in the final manifests is: FAN YANXI — GPT-4o-mini V2; HOU YUXUAN — Qwen 3 30B V2; LIN SIYUAN — Mistral Small 3.2 V2; WEN HAO — Gemini 2.5 Flash V2; CHEN CHANG — Claude Opus 5 V2; ZHOU YU — Qwen V1 prompt control. Operator attribution is metadata and does not change saved traces, scores, tokens, or costs.

## 16–19. Files, validation, D6 and API use

Updated existing outputs: `D5_COMPARISON.md`, `D5_COST_RECONCILIATION.md`, `GITHUB_SNIPPETS.md`, and the package's `build_d5_comparison.py` entrypoint, which now calls the offline normalized builder. Added D5-only builder/tests, the three audit/QA files, six selected derived CSVs, `SELECTED_FINAL_INDEX.json`, and the Claude result-package copy. Removed the obsolete `CLAUDE_COMPARABILITY_BLOCKER.md` and the final-package Llama result directory. No unrelated file was changed.

Validation: offline generator and package entrypoint passed; all six selected batteries and 278 source rows asserted; five V2 families, matched negative and Qwen keys, exact denominators, Claude usage/cost, preserved raw token/cost fields, zero pass-label changes, the explicit Mistral escalation-record failure, invalid-output failures, selected-spend sum and Llama absence asserted. D5-specific local tests: **5/5 passed**. Original Agent unit tests: **94/94 passed**. No model, OpenRouter, LLM or other external API was called.

**D6 freeze:** no file under `D6_cost_analysis/` was written. Its 62 files all retain timestamps before this D5 rewrite; the latest is 2026-09-18 10:54:31 local time. The Agent Git working tree was clean after testing. D6 changes caused by this task: **zero**.

## 20. Remaining limitations

The unavailable Claude commit prevents a complete source-tree diff; matching saved configurations and raw case payloads do not prove every unobserved source detail identical. Historical AI-assisted claim verdicts have no evidenced named-human sign-off; the formerly unreviewed Mistral escalation claim remains unaccepted because its saved final record omits deliberate non-use of an observed available slot. Claude covers only the 18 common negative trials, and the 52-run full-battery design does not satisfy the later 56-run shape. Historical account-level spend and residual cannot be allocated exactly to the final selected experimental set.
