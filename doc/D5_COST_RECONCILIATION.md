# D5 final cost reconciliation

The authoritative generated reconciliation is
[`results/d5/D5_COST_RECONCILIATION.md`](../results/d5/D5_COST_RECONCILIATION.md).
This page summarizes the current selected experiment and separates it from the
superseded account snapshot.

## Current selected experiment

| Selected scored experiment | Scope | Provider USD | Coverage |
|---|---|---:|---:|
| GPT-4o-mini V2 | Full battery | 0.06240015 | 52/52 |
| Qwen 3 30B V2 | Full battery | 0.07621029 | 52/52 |
| Mistral Small 3.2 V2 | Full battery | 0.10114050 | 52/52 |
| Gemini 2.5 Flash V2 | Full battery | 0.18117530 | 52/52 |
| Claude Opus 5 V2 | Negative-only | 1.64440500 | 18/18 |
| Qwen 3 30B V1 | Prompt control | 0.06968878 | 52/52 |

**Selected scored-run spend = US$2.13502002** for 278 scored runs, with
provider-reported cost coverage of 278/278.

One additional failed Mistral provider attempt incurred **US$0.00031845**. It
is not a scored trial and is excluded from pass-rate and unit-cost
denominators. Including that attempt, recorded selected-model charges are
**US$2.13533847**.

## Historical account evidence

The earlier OpenRouter account snapshot increased by **US$0.653968992** and
left **US$0.018762122** unattributed. That snapshot predates the final Claude
package and includes or may include superseded Llama-era and precheck activity.
It is retained as historical account evidence only and is not reconciled to the
current 5+1 selected experiment.

Reporting rules:

- use **US$2.13502002** for selected scored-run spend;
- use **US$2.13533847** only when explicitly including the extra provider-error
  charge;
- do not report the historical account increment as the final 5+1 spend;
- do not assign the historical residual to any model without billing evidence;
- provider-vs-list-rate differences are diagnostics, not proof of billing
  error.
