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

## ZHOU YU D7 contribution

ZHOU YU designed and implemented the two deterministic D7 failure
reproductions, generated the before-and-after metrics, measured the 40-case turn
distribution, added the D7 regression tests, and documented the reproduction
commands and findings.

## D5 model ownership

FAN YANXI ran Qwen 3 30B V2, HOU YUXUAN ran Mistral Small 3.2 V2,
LIN SIYUAN ran GPT-4o-mini V2, WEN HAO ran Llama 3.3 70B V2, and ZHOU YU
ran Gemini 2.5 Flash V2. CHEN CHANG owned the Qwen 3 30B V1/V2 prompt
comparison: CHEN CHANG ran the additional V1 battery and compared it with
FAN YANXI's matching Qwen V2 battery. Together the team preserved 312 formal
live traces and their cost evidence.
