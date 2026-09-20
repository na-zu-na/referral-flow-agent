# Contributions

The table records the agreed team ownership. Commit history and result files
provide the supporting evidence for completed work.

| Work strand | Owner or owners |
|---|---|
| Agent loop and tools | CHEN CHANG, FAN YANXI |
| Tool descriptors, v1 to v2 rewrite and guardrail layer | CHEN CHANG, HOU YUXUAN |
| Evaluation harness and scripted run | LIN SIYUAN, FAN YANXI |
| Cost model, ledger and sensitivity analysis | HOU YUXUAN, WEN HAO |
| Evaluation cases | CHEN CHANG, FAN YANXI, HOU YUXUAN, LIN SIYUAN, WEN HAO, ZHOU YU |
| Live model battery | CHEN CHANG, FAN YANXI, HOU YUXUAN, LIN SIYUAN, WEN HAO, ZHOU YU |
| D7 two reproduced failures | **ZHOU YU** |
| Team report and demonstration assembly | ZHOU YU |
| Final demonstration video editing | HOU YUXUAN |

## CHEN CHANG individual contribution

GitHub: [na-zu-na](https://github.com/na-zu-na)

CHEN CHANG was primarily responsible for repository integration, refinement,
validation, and final delivery preparation. Building on implementations
contributed by other team members, CHEN CHANG integrated and improved the D2
experiments, D4 evaluation workflow, D5 live-model battery, and D7
failure-reproduction evidence. This work included correcting evaluation
semantics and rubric handling, preserving live usage and cost evidence,
aligning operator and model metadata, consolidating the final D5 evidence
package, and validating the integrated outputs.

CHEN CHANG also integrated the existing D6 cost-analysis package into the main
repository, reorganised the D5/D6 directory structure, repaired paths and
tests, synchronised provenance, and connected the evidence to the Web
demonstration. Additional contributions included repository setup, dataset and
fixture expansion, live experiment execution, documentation maintenance, UI
development, consistency checking, and final delivery preparation.

The underlying D2 descriptor experiments, D4 evaluation harness, D5 battery
framework, D6 calculation package, and D7 failure-reproduction implementation
were based on work initially produced by other team members. CHEN CHANG's
contribution focused on their integration, extension, correction, validation,
and presentation.

## FAN YANXI individual contribution

GitHub: [yancey07-piiiigy](https://github.com/yancey07-piiiigy)

FAN YANXI was primarily responsible for the design, implementation, refinement, and validation of the project’s core single-agent ReAct architecture. This work included developing the model–tool–observation loop, implementing structured AgentMove parsing and validation, maintaining isolated state and complete evidence traces for each run, and supporting parallel execution of independent referral checks. FAN YANXI also integrated the Agent controller with the project’s tools and guardrails to ensure that every final decision was grounded in trusted observations and limited to one of three permitted outcomes: book, request information, or escalate.

FAN YANXI also contributed to the prompt-development and evaluation workflow, including the implementation and testing of the V1 and V2 system prompts and their integration with the Agent runtime. For the live-model battery, FAN YANXI was responsible for executing the GPT-4o-mini V2 experiment across the formal evaluation cases, preserving the raw execution traces, token usage, provider costs, and scored outputs. Additional contributions included analysing invalid structured outputs and negative-case behaviour, validating the safe-booking workflow, supporting scripted evaluation, maintaining Agent-related documentation, and preparing the Agent architecture and safe-booking sections of the final demonstration.

The underlying tool implementations, guardrail components, evaluation harness, cost-analysis package, Web interface, and other live-model experiments were based on work initially produced by other team members. FAN YANXI’s contribution focused on the core Agent controller, prompt integration, GPT-4o-mini V2 experiment execution and analysis, Agent-level testing and validation, and the presentation of the system’s reasoning and safe-booking workflow.

## HOU YUXUAN individual contribution
#### Github: [yisionhou](https://github.com/yisionhou)

My main contribution was the Prompt V1/V2 work, the Qwen 3 30B V2 experiment, and D6 Cost / FinOps analysis. I helped turn the referral rules into two testable prompts. V1 was the detailed baseline, while V2 clarified the tool sequence: retrieve the referral first, run the criteria and patient checks in parallel, search for slots only after these checks, and request confirmation before booking. I also strengthened the stop rules for hostile input, missing tests, red flags, and duplicate appointments, and required the model to use only observed clinical and booking information. This made the workflow easier to follow and test consistently.

I compared the prompts using the same Qwen model and 52 evaluation runs. Passes improved from 20/52 with V1 to 28/52 with V2, an increase of 15.38 percentage points, while invalid outputs dropped from 26 to 14. Unsafe booking attempts still increased from three to seven, showing that prompt improvements cannot replace code-level guardrails. I kept this trade-off visible instead of reporting only the higher pass rate. My assigned D5 experiment was Qwen 3 30B V2. ZHOU YU handled the formal Qwen V1 control run, while I covered the prompt design, integration, and comparison.

For D6, I built the Cost / FinOps analysis from the frozen D5 results without rerunning models or changing the evidence. All 278 scored runs had recorded provider cost. Using 4,000 referrals per month, USD 55 per nurse hour, and ten minutes of nurse work per failure, one failure costs about USD 9.17. The estimated monthly scenarios were USD 24.7k for GPT, USD 16.9k for Qwen, USD 10.6k for Mistral, and USD 9.2k for Gemini. Claude stayed outside the final general monthly comparison. I also completed sensitivity, break-even, Pareto, bootstrap, spend, and cost-lever analyses. The Qwen V1-to-V2 improvement reduced estimated monthly fallback by about USD 5.6k, and the recorded cost for all scored runs was USD 2.13502002.

I prepared the D6 pipeline, reports, charts, 11-sheet Excel workbook, QA documents, and four-slide video material. I also completed the final video editing by arranging the front-end recordings, backend evidence, narration, and project cover into a clear sequence. Final checks included 11/11 D6 tests, 5/5 D5 tests, 94/94 Agent tests, and 2,169 independent checks, with no release blockers. My main conclusion is that reliability affects estimated operating cost much more than small token-price differences. These figures are evaluation scenarios rather than real hospital spending, zero fixed cost is only a baseline assumption, and Claude remains negative-only with no general monthly extrapolation.

## LIN SIYUAN individual contribution

- Developed the Python evaluation scorer for D4, covering decisions,
  escalation triggers, slot constraints, and prohibited booking attempts.
- Reviewed the test cases and answer keys, incorporated the agreed rubric
  corrections, and separated hard failures from diagnostic warnings and
  claims requiring human review.
- Verified the final scripted V1/V2 results: each passed 52/52 runs, including
  18/18 negative runs, with no pending reviews. Prepared the summaries, trial
  records, and reproducible evaluation commands.
- Contributed the Mistral Small 3.2 V2 evaluation to D5, documenting 37/52
  passing live runs, failure categories, token usage, and recorded costs.
- Prepared the D4 demonstration video and supporting explanation, clearly
  distinguishing scripted evaluation results from live-model performance.

## WEN HAO individual contribution

I wrote the D0 section, placing outpatient referral coordination on Class 4’s seven-rung ladder and explaining why its variable, evidence-driven sequence requires a rung-7 agent. I applied the workflow, ground-truth, governance-cliff and reliability tests, used project evidence to analyse compounded turn reliability, and defined five good-run criteria. I also ran the Gemini 2.5 Flash V2 live evaluation, consolidating its 39/52 overall pass result, 12/18 negative-case result and zero unsafe booking attempts. Finally, I wrote and analysed D6’s three-layer cost-to-serve model, sensitivity analysis and break-even calculations, showing that reliability and reduced human fallback outweighed small token-cost differences.

## ZHOU YU individual contribution

1. Led and completed the D7 controlled-failure experiments, covering repeated tool calls after action de-duplication was removed and unsafe dependency ordering after one planning rule was removed from the prompt. Compiled the before-and-after results, cost analysis, and recommendations for improvement.

2. Conducted the Qwen 3 30B V1 matched prompt-control battery for D5 and preserved its live-run evidence.

3. Managed the overall compilation and drafting of the team report, including verifying key figures and tables.

4. Participated in planning the screen-recorded demonstration for the individual component.

## D5 model ownership

The final selected operator responsibility is:

| Team member | Selected experiment |
|---|---|
| FAN YANXI | GPT-4o-mini V2 full battery |
| HOU YUXUAN | Qwen 3 30B V2 full battery |
| LIN SIYUAN | Mistral Small 3.2 V2 full battery |
| WEN HAO | Gemini 2.5 Flash V2 full battery |
| CHEN CHANG | Claude Opus 5 V2 Frontier negative-only battery |
| ZHOU YU | Qwen 3 30B V1 matched prompt control |

The final package contains 278 selected scored live runs: four 52-run V2 full
batteries, 18 Claude negative-only runs, and 52 Qwen V1 prompt-control runs.
All 278 selected scored rows have provider-reported cost evidence. The
superseded Llama run remains historical evidence only and is not part of the
final selected inventory.

## D5 frontier supplement

**CHEN CHANG** completed the selected `anthropic/claude-opus-5` V2
negative-only battery: six negative cases with three trials each (18 live
runs), including resumable evidence capture, cost recording, and preservation
of the reviewed result set. The result is reported only as a negative-subset
stress test and is not presented as a full-battery or production pass rate.
OpenAI Codex performed the disclosed AI judgement review on 2026-09-18;
named-human sign-off is not evidenced and remains a documented limitation.
