# PE6201 A2 — Problem B Referral Flow Agent

This repository combines the existing Problem B data, tools, and deterministic
guardrails with the complete Member 1 single-agent ReAct controller.

The default is free and offline:

```bash
python3 main.py REF-5602 --verbose
```

Run every automated test:

```bash
python3 -m unittest discover -s tests -v
```

Show the exact v1 or v2 prompt:

```bash
python3 main.py --descriptors v2 --show-prompt
```

Controlled sequential/parallel comparison:

```bash
python3 main.py REF-5602 --call-mode sequential
python3 main.py REF-5602 --call-mode parallel
```

Run the complete D2 descriptor/return-shape and same-turn batching experiment
(40 core cases, three isolated trials per variant):

```bash
python3 experiments/run_d2_experiments.py
```

The design table, poka-yoke evidence, measurements, and live reproduction
command are in [`D2_TOOL_EVIDENCE.md`](D2_TOOL_EVIDENCE.md).

Reproduce the two D7 controlled failures and regenerate their evidence:

```bash
python3 -m experiments.d7_failures
```

The experiment contract, report-ready analysis, and Chinese demo script are in
[`doc/D7_README.md`](doc/D7_README.md),
[`doc/D7_REPORT_SECTION.md`](doc/D7_REPORT_SECTION.md), and
[`doc/D7_DEMO_SCRIPT_CN.md`](doc/D7_DEMO_SCRIPT_CN.md).

Run a live OpenRouter model only when intentionally doing the model battery:

```bash
export OPENROUTER_API_KEY="your-key"
python3 main.py REF-5602 --backend live --model openai/gpt-4o-mini --verbose
```

In live `confirm` mode the controller pauses before `book_slot` unless a trusted
UI/CLI supplies an approval callback. Model text cannot approve itself.

See `MEMBER1_IMPLEMENTATION_GUIDE_CN.md` for the detailed Chinese walkthrough.
