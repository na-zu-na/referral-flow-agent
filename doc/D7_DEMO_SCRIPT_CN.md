# D7 录屏讲稿

建议时长约 60 秒。

“我负责复现两个失败，并且两个实验都从正常 Agent 中只删除一个组件。

第一个是循环控制。我删除持久化 action de-duplication，让同一个 backend 用不同 call ID 重复读取 REF-5602。40 个 core cases 的合法运行中位数和最大值都是 4 turns，40 个全部通过且没有触发 cap，所以实验 cap 设为 5。删除去重后，循环一直到第 5 turn 才被 STEP_LIMIT_REACHED 停止，估算成本是 0.0028111 美元；恢复去重后，第 2 次等价动作立即被 DUPLICATE_ACTION_BLOCKED 阻止，只完成 1 turn，估算成本降低 69.1%。去重负责识别循环，step cap 是最后的安全兜底。

第二个是 prompt 失败。我从正常 v2 system prompt 中只删除一句依赖顺序规则，其他 case、descriptor、backend、controller、tools、guardrails、call mode 和 cap 全部保持一致。缺少这句话时，同一个 prompt-aware backend 把 slot 查询和它的前置检查放在同一 turn，真实 guardrail 明确报出 DEPENDENCY_VIOLATION，案例失败。恢复这句话后，Agent 等前置 observation 成功再查号源，并正确得到 no_slot_in_window，案例通过。这个修复属于 prompt 层，因为问题是模型规划顺序，不是工具返回值，也不是循环或预算控制。”
