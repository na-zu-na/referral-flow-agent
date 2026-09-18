# D5 selected experiment spend and historical account evidence

| Selected scored experiment | Scope | Recorded provider USD | Coverage |
| --- | --- | --- | --- |
| openai_gpt4o_mini_v2 | full_battery | 0.06240015 | 52/52 |
| qwen3_30b_v2 | full_battery | 0.07621029 | 52/52 |
| mistral_small_3_2_v2 | full_battery | 0.10114050 | 52/52 |
| gemini2_5_flash_v2 | full_battery | 0.18117530 | 52/52 |
| claude_opus5_frontier_negative_v2 | negative_only | 1.644405 | 18/18 |
| qwen3_30b_v1 | prompt_control | 0.06968878 | 52/52 |

**SELECTED_FINAL_EXPERIMENT_SPEND = US$2.13502002** for 278 scored selected runs with 278/278 provider-reported charges. This includes four 52-run V2 batteries, Claude's 18 negative-only runs and Qwen V1's 52-run prompt control. It excludes superseded Llama. Scoring normalization changes no token or charge field.

The extra charged Mistral provider-error attempt is **US$0.00031845**, separate from scored-run spend. Including this attempt gives US$2.13533847 of recorded selected-model evaluation charges, but it is not a 279th scored trial and is not inserted into per-model pass or unit-cost denominators.

The historical D5 document reported an OpenRouter account snapshot rising from US$0.271794400 to US$0.925763392, an increment of US$0.653968992. That snapshot covered the previous model selection and predates the new Claude package; it is **HISTORICAL_ACCOUNT_SPEND**, not a current invoice for the 5+1 set. It includes or may include superseded activity and unassigned charges. Previous account-level residual US$0.018762122 remains unattributed; no share is assigned to Claude, Llama or another run without billing evidence. The old Llama formal provider amount was not fully measured (51/52 charges) and is excluded from selected spend but remains historical source evidence outside this final selection. No reconciliation is forced between snapshots taken at different times.
