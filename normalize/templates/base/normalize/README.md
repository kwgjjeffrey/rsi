# 本项目的归一化工作区

这是可写的项目能力，不属于目标 Skill 的发行内容。先完成 assessment.md，再实现/配置脚本并验证。

| 目录/文件 | 职责 |
|---|---|
| assessment.md | Agent 对目标 Skill、数据源和运行方式的分析与接入决策 |
| manifest.json | 协议版本、来源模板、阶段入口、解释器和配置状态 |
| cases/ | 从文件/API/标注平台等取数，映射成标准 case records；缺标由 Agent 阅读并补齐 |
| replay/ | 创建独立会话，准备输入，等待结束并回收原始证据；处理 CLI、App Server 或目标 UI/CDP |
| results/ | 将各 Harness 原始输出转换为标准 Replay 输出，不负责评价或改写任务 |
| shared/ | 项目脚本真正共用的协议、路径和访问辅助逻辑 |
| tests/ | 本项目归一化适配器的样本与合同/集成断言，不是目标 Skill 的业务题库 |
| receipts/ | RSI 工具写入的阶段合同验证回执；不等于业务验收通过 |

各脚本用 stdin 接收 JSON，stdout 只输出 JSON，错误非零退出。不打印凭据。凭据从已有受限配置或环境读取，不写入 manifest。项目依赖的确定性准备方式也应记录在这里，不能引用作者的其他 checkout。

数据流：数据源 → cases/ → 初始化候选记录 → Agent 补标与反思 → 冻结问题集。
重放流：task_input → replay/ → 原始轨迹/产物 → results/ → 标准 Replay 输出 → RSI 组装同构 case record → 独立评价与反思。

原始工作材料与归一化候选、冻结数据集和各轮结果分别保存。现有 tooling/ 可以继续用，但新归一化脚手架集中到 normalize/，不要同时维护两份实现。
