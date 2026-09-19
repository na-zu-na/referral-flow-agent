# D5 final selected 5+1 comparison

This document is the human-facing entry point for the current D5 result. The
authoritative generated comparison is
[`results/d5/D5_COMPARISON.md`](../results/d5/D5_COMPARISON.md), and the
machine-readable selection is
[`results/d5/SELECTED_5PLUS1_INVENTORY.csv`](../results/d5/SELECTED_5PLUS1_INVENTORY.csv).
The superseded Llama result remains only in the historical `results/live/`
archive and is not part of the final selection, pass rates, or selected spend.

## Final inventory

The selected experiment contains five V2 model families across two
team-classified price tiers, plus one matched Qwen V1 prompt control.

| Experiment | Family | Scope | Runs | Result | Provider spend |
|---|---|---|---:|---:|---:|
| GPT-4o-mini V2 | OpenAI | Full battery | 52 | 17/52 (32.69%) | US$0.06240015 |
| Qwen 3 30B V2 | Qwen | Full battery | 52 | 28/52 (53.85%) | US$0.07621029 |
| Mistral Small 3.2 V2 | Mistral | Full battery | 52 | 37/52 (71.15%) | US$0.10114050 |
| Gemini 2.5 Flash V2 | Google | Full battery | 52 | 39/52 (75.00%) | US$0.18117530 |
| Claude Opus 5 V2 | Anthropic | Frontier negative-only | 18 | 10/18 (55.56%) | US$1.64440500 |
| Qwen 3 30B V1 | Qwen | Matched prompt control | 52 | 20/52 (38.46%) | US$0.06968878 |

The four full batteries use the same 40 cases: 34 ordinary cases once and six
negative cases three times, giving 52 runs/model. Claude uses only the common
18 negative trials under the Section 7 Frontier exception. Its ordinary-case
and full-battery rates are therefore **N/A**, and 10/18 must not be
extrapolated to production.

## Common negative subset

Exactly `REF-6060` through `REF-6065`, trials 1-3, are matched across the five
V2 models.

| Model | Pass | Invalid output | Unsafe booking attempts |
|---|---:|---:|---:|
| GPT-4o-mini | 14/18 | 4/18 | 0 |
| Qwen 3 30B | 6/18 | 2/18 | 7 |
| Mistral Small 3.2 | 9/18 | 0/18 | 4 |
| Gemini 2.5 Flash | 12/18 | 6/18 | 0 |
| Claude Opus 5 | 10/18 | 8/18 | 0 |

This is a negative-subset stress test, not a production estimate.

## Matched prompt control

Qwen V1 and V2 use the same model and the same 52 case/trial keys. V1 passed
20/52 and V2 passed 28/52, an observed improvement of **15.38 percentage
points**. No selected pass label changed during offline scoring normalization;
raw traces, model outputs, token usage, and provider charges were not edited.

## Operator responsibility

| Operator | Experiment |
|---|---|
| FAN YANXI | GPT-4o-mini V2 |
| HOU YUXUAN | Qwen 3 30B V2 |
| LIN SIYUAN | Mistral Small 3.2 V2 |
| WEN HAO | Gemini 2.5 Flash V2 |
| CHEN CHANG | Claude Opus 5 V2 negative-only |
| ZHOU YU | Qwen 3 30B V1 prompt control |

## Evidence boundaries

- Final selected scored runs: **278**, with provider cost coverage **278/278**.
- Selected scored-run spend: **US$2.13502002**.
- Recorded selected-model charges including one extra Mistral provider-error
  call: **US$2.13533847**.
- The five V2 families are OpenAI, Qwen, Mistral, Google, and Anthropic.
- GPT/Qwen/Mistral/Gemini are the team's lower-price group; Claude is the
  Frontier comparison. This is a team experiment classification, not an
  official course mapping of the exact model IDs.
- The final design meets the 30-case/6-negative passing floor but does not
  claim the later recommended 40-case/8-negative/56-run shape.
- Claude's recorded source commit is unavailable locally for a complete source
  tree diff; the common negative keys and saved configuration match, with this
  provenance limitation retained.

See also:

- [`doc/D5_FINAL_QA.md`](D5_FINAL_QA.md)
- [`doc/D5_SCORING_NORMALIZATION_AUDIT.md`](D5_SCORING_NORMALIZATION_AUDIT.md)
- [`results/d5/D5_COST_RECONCILIATION.md`](../results/d5/D5_COST_RECONCILIATION.md)
