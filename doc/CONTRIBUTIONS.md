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

## CHEN CHANG integration contribution

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

## ZHOU YU D7 contribution

ZHOU YU designed and implemented the two deterministic D7 failure
reproductions, generated the before-and-after metrics, measured the 40-case turn
distribution, added the D7 regression tests, and documented the reproduction
commands and findings.

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
