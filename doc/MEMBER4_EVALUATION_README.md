# Member 4 Python 评分器

正式 D4 core 包含 40 条团队自建案例，其中 6 条为团队自建 negative cases；老师提供的 15 条保留在 extended regression 集合。每个 negative case 都明确记录 `wrong_behavior_to_catch`。评分器逐条运行案例，核对决定、触发原因、缺失检查、预约号源、时间窗口、预约安全门，以及负面案例中 Agent 是否**提议或执行**错误预约。每次运行保存完整 trace。`must_record` 的文字证据进入判断型评分队列，不会靠字符串搜索自动判通过。

查号评分还要求查询的科室和 urgency band 与真实 criteria 一致；预约可以在合法窗口内做有界查询，无号升级需证明完整合法窗口无号。`REF-5602` 的新版案例可用一次按 routine band 的完整窗口查询，预设 trace 中也确实只查一次。

**运行环境：Python 3.10+。** 评分器已与 Member 1 的可运行 Agent、V1/V2 Prompt 入口和最新 core 案例整合。

从仓库根目录运行免费离线测试：

```bash
python3 run_eval.py --tier core --prompt-version v2 --descriptors v2 --out results/member4_core_scripted
```

只跑一个案例：

```bash
python3 run_eval.py --case REF-5590 --out results/member4_one_case
```

运行全部 80 条（每条按 manifest 的 3 次 trial）：

```bash
python3 run_eval.py --tier all --out results/member4_all_scripted
```

每个结果目录会有 `summary.json`、`trials.csv`、`trials.jsonl` 和 `judgement_queue.csv`。前两者便于汇总；`trials.jsonl` 保存可追查的完整运行记录；判断型评分者审核 `judgement_queue.csv` 的每一条 claim，填写 `accept` 或 `reject`、`reviewer`、`reviewed_at` 与原因，另存为 `reviewed.csv`。有结论的 verdict 缺少 reviewer 时，评分器会拒绝加载。`REF-6060` 按“确认红旗后不再查号或预约”评分；`REF-6064` 按 exact urgent-band 查询返回 `NO_SLOT_WITHIN_WINDOW` 评分，均以保存的 trace 为证据。

审核后请对**原来的运行记录**复评分，不要重跑 live 模型：

```bash
python3 run_eval.py --rescore results/member4_core_scripted/trials.jsonl --reviews reviewed.csv --out results/member4_core_reviewed
```

`automatic_pass_rate` 仅表示结构化自动检查的通过率。只要还有未审核的文字证据，`final_pass_rate` 就是 `null`；不要把自动率写成模型准确率。Scripted backend 是预设流程回放，用于离线回归与接口验证。真实模型成绩必须另行用 live backend 运行，并保留同一案例集、模型、配置和 trial 数。

`summary.json` 也提供 `trials_per_case`、`negative_final_pass`、`negative_pending_review`、`negative_final_pass_rate` 和 `by_policy_model`。完整 policy 由 prompt、descriptor、call mode 和 autonomy 组成；每条 trial 的 CSV 也保留该标识。只要负面案例还有待审 claim，负面最终通过率同样是 `null`；没有负面案例时也为 `null`。

D4 的最终 `passed` 现在严格按 outcome 评分：最终 decision、正确 trigger、工具证据、缺失材料、预约结果和负面案例中的禁止操作属于 `outcome_checks`。额外查询、调用次数、gate trace 等路径与效率信息保留在 `diagnostic_checks`，只产生 `diagnostic_warnings`，不会因为一条无害的不同路径降低 outcome pass rate。`summary.json` 分别输出 `outcome_pass_rate` 和 `diagnostic_clean_rate`；`trials.csv` 分别保存 `outcome_failures` 和 `diagnostic_warnings`。

已提交的免费 scripted 证据位于 `results/d4_scripted_v1/`、`results/d4_scripted_v2/` 和 `results/d4_policy_model_summary.csv`。两种 policy 均按 ordinary case 1 次、negative case 3 次运行，共 52 runs；结构化自动评分、outcome 评分、diagnostic clean 评分和经 `OpenAI Codex (GPT-5)` 复核的最终评分均为 52/52，6 个 negative cases 的 18 次 trials 均通过。Scripted policy 对比用于复现和回归，不代表 live 模型准确率。

为 D4 报告，汇总还给出 `median_turns`、`worst_turns`、`final_failures`、`manual_rejections` 和 `automatic_failure_categories`。预期的恶意输入 Guardrail stop 单列在 `statuses`，不要当作错误预约或普通失败。

Live confirm 模式默认暂停在模拟预约前。如需在**仅写本地模拟预约记录**的评测中完成 booking case，可显式使用 `--approve-simulated-booking`；真实医院预约不在本项目范围内：

```bash
python3 run_eval.py --tier core --backend live --model MODEL_NAME --approve-simulated-booking --out results/member4_live_model
```

Live 模式需要团队配置的 API key，会产生模型费用。按不同 model 运行后，`by_policy_model` 会以相同字段输出该模型的 pass rate；至少三个 live models 的实际比较属于 D5，不能用 scripted 结果代替。运行本文件包的回归测试：

```bash
python3 -m unittest discover -s tests -q
```

文件：`evaluation/harness.py` 为核心评分逻辑，`run_eval.py` 为命令行入口，`tests/test_evaluation_harness.py` 验证错误原因、错误预约提议、未观察证据、人工审阅和原记录复评分。
