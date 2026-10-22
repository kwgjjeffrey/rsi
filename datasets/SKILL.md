# 问题集归一化

## 目的、交付与约束
每条 case record 统一包含 task_input、trajectory、annotation、reflection。初始化和 Replay 使用完全相同结构；Replay 不回写问题集。保留原始来源，文档摘要不能冒充原始工具轨迹。

## 主流程
1. 阅读数据源，提取真实输入、执行轨迹和标注；缺少人工标注则 Agent 阅读轨迹标注，写判断依据、标注者与置信度。无法确定时写 unknown，不能强行打分。
2. 每题完成 reflection：证据、根因假设、建议、未知项。历史评审可作为二手证据，但必须注明原始轨迹不可得和历史版本边界。
3. 使用 import 冻结一个新版本，重复版本拒绝覆盖。新增数据产生新版本。按[迭代模块](../evolution/SKILL.md)建立 Sprint。

## 工具输入输出
import 请求必填 op/project/dataset/version/records；前三类 ID 仅字母数字下划线连字符。records 是非空数组，每项包含唯一 case_id、record_id、task_input、数组 trajectory、对象 annotation、字符串 reflection。输出存储路径及数量，写 datasets/<id>/<version>/cases/<case_id>/record.json。

annotation 推荐字段：status=completed|unknown|pending，score=0..100（completed 必填）、rubric_version、criteria、judgments、annotator、confidence、source。每个判断包含 evidence 引用。criteria 内存预期/验收条件，judgments 存此次执行评价。reflection 写问题证据与归因；无问题也说明依据。

```json
{"op":"import","project":"my_skill","dataset":"seed","version":"v001","records":[{"case_id":"c1","record_id":"initial_c1","task_input":{"instruction":"执行目标任务"},"trajectory":[{"type":"source_excerpt","source":"本地记录路径","text":"真实执行片段"}],"annotation":{"status":"unknown","criteria":[],"annotator":"agent","reason":"原始结果缺失"},"reflection":"证据不足，补齐实际执行后再评价。"}]}
```

## 工具调用约定
以下命令执行安装目录内 Rust binary；`RSI` 为安装路径，`DATA` 为可写数据根，`REQUEST` 为 Agent 写好的 JSON 请求绝对路径。CLI 和 GUI 共用 dispatch，成功输出 JSON，校验失败非零退出。不要并发写同一项目。

```bash
RSI="$HOME/.agents/skills/rsi"
DATA="$HOME/.local/state/rsi/.data"
REQUEST="/tmp/rsi-request.json"
RSI_DATA_DIR="$DATA" "$RSI/local-runtime/bin/rsi-runtime" dispatch "$REQUEST"
```

矩阵结论建议在 annotation 中明确记录 `outcome: passed|failed`，与本次评价证据一致。completed 只表示标注已完成，不等于通过。没有显式 outcome 时，工作台参考 judgments 的明确结论；或使用 Sprint 冻结的 blueprint/evaluation.json 中 `pass_threshold`（可选 0..100 数字）解释分数。无阈值时只将满分/零分映射为通过/未通过，中间分数显示待确认，不猜测通过线。
