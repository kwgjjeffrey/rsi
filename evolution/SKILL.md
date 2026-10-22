# 迭代与独立重放

## 目的、交付与约束
每轮保留计划、源码版本、逐题完整记录、对比及整体 reflection。Round 0 是初始化镜像；其整体反思指导 Round 1。计划落盘后直接开展授权范围内修改，开发者可以查看和介入。

## 主流程
1. 请求 create-sprint，冻结问题集和 Blueprint。必填 project/sprint/dataset/version；source 记录 Git HEAD、dirty 状态和历史来源，budget 记录轮次、时间、成本上限。工具输出 Sprint 路径，已有 Sprint 拒绝覆盖。
2. 阅读 Round 0 所有 case reflection，按需回查轨迹和代码，写 `rounds/000/reflection.md`；区分已证实根因和假设。
3. 在 `rounds/001/plan.md` 写改进假设、改动、验证、停止条件，按目标仓约定修改并验证。不触碰已有无关改动。
4. 配置 Harness adapter，执行 replay；每题启动一个新进程，适配器必须真正创建新 Session，返回 session_id、loaded_skill_digest、数组 trajectory。不得把 annotation/reference/reflection 传入被测会话。Agent 需核对实际加载内容，fresh_session 声明本身不是隔离证明。
5. 使用独立评价上下文，按冻结规则逐题补齐 annotation 和 reflection；执行失败单列，不能假装能力失败或偷偷排除分母。
6. 执行 compare，阅读所有 case reflection 后写本轮整体 reflection.md，引用 case_id，汇总共性根因、回归和优先级。决定接受、回退、继续或按预算停止。当前比较基线为 Round 0；上一轮与最佳轮交互视图尚未提供。

## 工具
create-sprint 请求例：`{"op":"create-sprint","project":"my_skill","sprint":"s001","dataset":"seed","version":"v001","source":{"revision":"实际 Git HEAD"},"budget":{"max_rounds":3}}`。通过[接入模块 dispatch](../onboarding/SKILL.md)执行，写快照而不改源码。

`manage_evolution_round.py` 的 replay/compare：必填 --project-root 数据根中的项目绝对路径、--sprint ID、--round 正整数；replay 另需 --adapter 配置路径，可选 --timeout 秒，默认 600。配置 `{"fresh_session":true,"command":["/absolute/harness-adapter"]}`，命令从 stdin 接收任务/源码 JSON，stdout 返回执行 JSON，不能复用父会话；stderr 用于诊断且不要输出凭据。适配器按项目实现，RSI 不假定某个平台可用。Replay 写本轮 records 和源码 patch，拒绝重复运行及未跟踪源码，执行异常记录 error。compare 写 comparison.json，只比较输入、规则版本和 criteria 一致且已完成评价的题，显示不可比数量和配对均值。

```bash
RSI="$HOME/.agents/skills/rsi"
PROJECT="$HOME/.local/state/rsi/.data/projects/my_skill"
python3 "$RSI/evolution/scripts/manage_evolution_round.py" replay --project-root "$PROJECT" --sprint s001 --round 1 --adapter "$PROJECT/blueprint/replay.json"
python3 "$RSI/evolution/scripts/manage_evolution_round.py" compare --project-root "$PROJECT" --sprint s001 --round 1
```

CLI 不自动调用修改 Agent 或评价 Agent；消费此 Skill 的 Agent 负责完整循环和预算判断。未知结果先核对，不重复发起有副作用的任务。
