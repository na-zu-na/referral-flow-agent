# D5 Live Model Battery 执行说明

## 已合并的 live 证据

`results/live/` 保留了 312 次正式 live runs：Qwen 3 30B、Mistral
Small 3.2、GPT-4o-mini、Llama 3.3 70B 和 Gemini 2.5 Flash 各 52 次 V2，
另有 Qwen 3 30B 的 52 次 V1 对照。第五个正式 V2 模型是 Llama，不是
Claude。这些结果使用符合最低通过配置的 52-run 计划：40 个案例中包含
6 个 negative cases；ordinary case 运行 1 次，negative case 运行 3 次。

- 模型对比：`D5_COMPARISON.md`
- 费用对账：`D5_COST_RECONCILIATION.md`
- 原始和审核记录：`results/live/`

用当前评分器重现这批历史结果（不调用模型）：

```bash
python3 build_d5_comparison.py \
  --battery results/live/qwen3_30b_v2 \
  --battery results/live/mistral_small_3_2_v2 \
  --battery results/live/openai_gpt4o_mini_v2 \
  --battery results/live/llama3_3_70b_v2 \
  --battery results/live/gemini2_5_flash_v2 \
  --battery results/live/qwen3_30b_v1 \
  --out D5_COMPARISON.md
```

52 runs 是本仓库声明的最低通过配置，不代表推荐的 40 cases / 8 negative
cases 配置。历史源码提交 `3d842b7` 的测试结果为 82/82；当前仓库的测试数另行记录，不用
82/82 描述当前 HEAD。

## 已完成的离线基线

仓库已经保存最终 40 个 core cases 的 reviewed scripted 结果：

- `results/d4_scripted_v2/summary.json`
- `results/d4_scripted_v2/trials.csv`
- `results/d4_scripted_v2/trials.jsonl`
- `results/d4_scripted_v2/judgement_queue.csv`

ordinary cases 各运行 1 次、6 个 negative cases 各运行 3 次，共 52 runs；最终评分 52/52，negative trials 为 18/18，pending review 为 0。不要再提交 package 中未复核、`final_pass_rate=null` 的重复 scripted 副本。

## 团队实验设计

本团队由 5 位成员分别运行 5 个不同的 V2 live models。CHEN CHANG 负责 Qwen 3 30B 的 V1/V2 prompt comparison：额外运行 Qwen V1，并与 FAN YANXI 运行的同模型 Qwen V2 结果比较。每个 battery 使用同一个 Git commit、40 个案例、V2 descriptors、parallel calls、confirm autonomy 和 temperature 0；V1 对照只改变 prompt version。

PDF 的运行规模按严格口径执行：

- 40 个案例各运行 1 次；
- 6 个 negative cases 各额外运行 2 次，即每个 negative 总共 3 次；
- 每个 battery 共 52 runs，其中 negative runs 共 18 次；
- 5 个 V2 batteries 加 1 个 V1 battery，共 312 runs。

`run_d5_battery.py` 会读取真实 Git HEAD，并拒绝 tracked files 尚未提交的工作区。所有 live batteries 必须在同一个提交上运行。

## 运行前

1. 提交并推送所有 D5 代码。
2. 确认五个 OpenRouter model IDs 当前可用。
3. 查询运行当天价格并估算每个 battery 的费用。
4. 设置 `OPENROUTER_API_KEY`，不要把 key 写入文件或聊天。
5. 如果 provider 不返回费用，设置每百万 token 的输入和输出价格：

```bash
export A2_PRICE_INPUT="0.10"
export A2_PRICE_OUTPUT="0.40"
```

## 运行和续跑

每个 model 使用不同输出目录：

```bash
python3 run_d5_battery.py \
  --model 'PROVIDER/MODEL_A' \
  --prompt-version v2 \
  --operator 'ACTUAL OPERATOR' \
  --max-cost-usd 1.50 \
  --out results/d5_model_a_v2
```

中断、provider error 或费用上限停止后，保持相同 model、prompt version、operator 和 Git commit：

```bash
python3 run_d5_battery.py \
  --model 'PROVIDER/MODEL_A' \
  --prompt-version v2 \
  --operator 'ACTUAL OPERATOR' \
  --max-cost-usd 1.50 \
  --out results/d5_model_a_v2 \
  --resume
```

选定其中一个已经运行 V2 的低成本模型，再用独立目录运行 V1：

```bash
python3 run_d5_battery.py \
  --model 'PROVIDER/MODEL_A' \
  --prompt-version v1 \
  --operator 'ACTUAL OPERATOR' \
  --max-cost-usd 1.50 \
  --out results/d5_model_a_v1
```

脚本逐次 `fsync` 保存 `raw_checkpoint.jsonl`，并更新 `progress.json`。只有包含 API 实测 token 用量且费用可计算的记录才会计入完成数；不合格记录会写入 `provider_errors.jsonl` 并停止。费用上限在下一次运行前检查，因此最多可能超过一个 case 的费用。

Frontier 模型按更新后的作业说明只运行 negative cases。当前 6 个 negative
cases 各运行 3 次，共 18 runs：

```bash
python3 run_d5_battery.py \
  --model 'anthropic/claude-opus-5' \
  --prompt-version v2 \
  --negative-only \
  --operator 'ACTUAL OPERATOR' \
  --max-cost-usd 1.34 \
  --out results/live/claude_opus5_frontier_negative_v2
```

该结果只能报告 negative pass rate、unsafe booking attempts、tokens 和 cost，
不能与完整 52-run battery 的 overall pass rate 直接比较。

## Judgement review

完成条件是 `progress.json` 中 `complete=true`、`completed=52`。复制 `scored_unreviewed/judgement_queue.csv` 为 `reviewed.csv`，逐条填写 `accept`/`reject`、真实 reviewer 和日期，然后只对已保存 traces 复评分：

```bash
python3 run_eval.py \
  --rescore results/d5_model_a_v2/raw_checkpoint.jsonl \
  --reviews results/d5_model_a_v2/reviewed.csv \
  --out results/d5_model_a_v2/scored_reviewed
```

复评分不会再次调用模型。每个最终 battery 至少保留：

- `battery_manifest.json`
- `raw_checkpoint.jsonl`
- `progress.json`
- `reviewed.csv`
- `scored_reviewed/summary.json`
- `scored_reviewed/trials.csv`
- `scored_reviewed/runs.csv`
- `scored_reviewed/tool_calls.csv`
- `provider_errors.jsonl`（如果出现 provider error）

## 汇总五模型和 V1/V2 对照

所有 6 个 batteries 完成复核后运行：

```bash
python3 build_d5_comparison.py \
  --battery results/d5_model_a_v2 \
  --battery results/d5_model_b_v2 \
  --battery results/d5_model_c_v2 \
  --battery results/d5_model_d_v2 \
  --battery results/d5_model_e_v2 \
  --battery results/d5_model_a_v1 \
  --out results/D5_COMPARISON.md
```

汇总器会拒绝不完整、未审核、非 live、没有 API 实测 token 用量、raw/reviewed 记录不一致、model 重复、配置不同、Git commit 不同或分母错误的结果，并输出总体通过率、negative pass rate、错误预约尝试、tokens、费用、cost source、case-level divergences、failure categories 和同模型 V1/V2 对照。

最终报告还需要人工解释模型家族、价格档、具体失败案例、最便宜达标模型，以及昂贵模型是否值得差价。实际 token 与费用数据应交给 D6 使用。
