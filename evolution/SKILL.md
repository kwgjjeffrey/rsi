# 迭代与独立重放

## 目的、交付与约束
每轮保留问题归因、改进计划、源码版本、逐题记录和对比。先按[归因与改进方法](analyze-and-plan.md)形成项目的 `blueprint/analysis.md` 和 `blueprint/improvement-plan.md`，再改代码。文件引用、分数和重复逐题摘要不能替代这两份文档。

默认按1、2、3、5、8…题的小窗口推进，超过50%不合格或执行/评价不完整就停止扩样，先归因、修复并复测已观察问题。每批更新分析和计划，不等整题库跑完。项目约定的维度可以是分类判断，不强制总分。

## 主流程
1. 请求 create-sprint，冻结问题集和 Blueprint。必填 project/sprint/dataset/version；source 记录 Git HEAD、dirty 状态和历史来源，budget 记录轮次、时间、成本上限。工具输出 Sprint 路径，已有 Sprint 拒绝覆盖。
2. 阅读 Round 0 所有 case reflection，按需回查轨迹和代码，写 `rounds/000/reflection.md`；区分已证实根因和假设。
3. 在 `rounds/001/plan.md` 写改进假设、改动、验证、停止条件，按目标仓约定修改并验证。不触碰已有无关改动。
4. 按[归一化模块](../normalize/SKILL.md)建设项目 normalize/replay/ 与 normalize/results/，配置 blueprint/replay.json 的 normalization_protocol=1、fresh_session=true。执行 replay；每题启动一个新进程，适配器必须真正创建新 Session，返回 session_id、loaded_skill_digest、数组 trajectory。不得把 annotation/reference/reflection 传入被测会话。Agent 需核对实际加载内容，fresh_session 声明本身不是隔离证明。
5. 使用独立评价上下文，按冻结规则逐题补齐 annotation 和 reflection；执行失败单列，不能假装能力失败或偷偷排除分母。逐项分类评价可不设score；不为使用比较工具编一个综合数。
6. 执行 compare，阅读所有 case reflection 后写本轮整体 reflection.md，引用 case_id，汇总共性根因、回归和优先级。决定接受、回退、继续或按预算停止。默认比较 Round 0；用 --baseline-round 指定更早的实际轮次。新窗口的执行前标注不是已测基线，不能声称提升。

## 工具
create-sprint 请求例：`{"op":"create-sprint","project":"my_skill","sprint":"s001","dataset":"seed","version":"v001","source":{"revision":"实际 Git HEAD"},"budget":{"max_rounds":3}}`。通过[接入模块 dispatch](../onboarding/SKILL.md)执行，写快照而不改源码。

`manage_evolution_round.py` 的 replay/compare：必填 --project-root 数据根中的项目绝对路径、--sprint ID、--round 正整数；replay 另需 --adapter 配置路径，可选 --timeout 秒，默认 600。配置 `{"fresh_session":true,"command":["/absolute/harness-adapter"]}`，命令从 stdin 接收任务/源码 JSON，stdout 返回执行 JSON，不能复用父会话；stderr 用于诊断且不要输出凭据。适配器按项目实现，RSI 不假定某个平台可用。Replay 写本轮 records 和源码 patch，拒绝重复运行及未跟踪源码，执行异常记录 error。compare 写 comparison.json，只比较输入、规则版本和 criteria 一致且已完成评价的题。逐项判断分别保留 before/after，同时有改善和退步时标为 mixed，不换算综合分；显式数值评价仍支持配对均值。不可比题单列。

```bash
RSI="$HOME/.agents/skills/rsi"
PROJECT="$HOME/.local/state/rsi/.data/projects/my_skill"
python3 "$RSI/evolution/scripts/manage_evolution_round.py" replay --project-root "$PROJECT" --sprint s001 --round 1 --adapter "$PROJECT/blueprint/replay.json"
python3 "$RSI/evolution/scripts/manage_evolution_round.py" compare --project-root "$PROJECT" --sprint s001 --round 1
```

CLI 不自动调用修改 Agent 或评价 Agent；消费此 Skill 的 Agent 负责真实归因、修改和评价。未知结果先核对，不重复发起有副作用的任务。新项目优先使用下方窗口工具限定范围；手工 replay 仍须遵守同一扩样门禁。

## Fibonacci窗口

`manage_evolution_campaign.py` 从冻结问题库准备一个窗口，`run`只运行该窗口；`assess`读取已完成的项目评价及整体反思，决定扩样、修复或执行阻塞。没有分析/改进计划不能准备窗口，没有真实评价不能扩样。修复窗口保留旧的真实记录作基线，不覆盖既有轮次。

```bash
RSI="$HOME/.agents/skills/rsi"
PROJECT="$HOME/.local/state/rsi/.data/projects/my_skill"
python3 "$RSI/evolution/scripts/manage_evolution_campaign.py" init --project-root "$PROJECT" --campaign daily --dataset daily_dialogues --version v1
python3 "$RSI/evolution/scripts/manage_evolution_campaign.py" prepare --project-root "$PROJECT" --campaign daily
# 阅读本窗口冻结的分析与计划，完成授权的代码修改和制品安装后：
python3 "$RSI/evolution/scripts/manage_evolution_campaign.py" run --project-root "$PROJECT" --campaign daily --timeout 900
# 逐题评价、更新根因/计划并写本轮reflection.md，然后：
python3 "$RSI/evolution/scripts/manage_evolution_campaign.py" assess --project-root "$PROJECT" --campaign daily
```

只有expand才进入新问题窗口；repair和hold_execution只准备已有未解决题。状态在项目 `blueprint/campaigns/`，可在工作台预览。工具不自动运行下一批、不修改评分、不把文件存在当成分析质量通过。

新项目 Replay 配置为 `{"normalization_protocol":1,"fresh_session":true}`，实际入口由项目 normalize/manifest.json 选择。命令先执行项目 replay 入口得到原始信封，再执行 results 转换；每题 raw/ 保留信封、轨迹和标准结果，record.json 仍使用初始化同构结构。沿用旧 command 配置时保持旧调用方式。两种路径都保留原输入、criteria 和 rubric_version，重新评价，不沿用原分数。
