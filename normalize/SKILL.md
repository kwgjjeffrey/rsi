# 项目归一化脚手架

## 目的、交付与约束

为目标 Skill 建设三段项目专属能力：工作记录归一化、独立 Replay 执行、结果回收归一化。交付 `.data/projects/<project_id>/normalize/` 内的评估、入口配置、脚本、样本和验证回执。脚本属于 RSI 项目的可写状态，不放到目标 Skill 的发行目录；必须部署到目标环境的最小运行组件才按目标仓约定落在目标源码中。

RSI 核心拥有标准记录、协议校验和轮次存储；项目脚本拥有真实数据源、字段映射、Harness/API/UI/CDP 的接线。目录生成、配置完成、协议校验、真实集成验证和目标任务评测是不同的完成状态。

## 标准流程

1. **由 Agent 分析目标，而非先套脚本。** 阅读目标 Skill 的入口、必要模块、源码和可访问样本，填写项目 `normalize/assessment.md`。必须确定：数据来源/格式/权限、稳定 case_id、缺标补标方法、Harness、新会话与实际加载验证、输入与副作用、结束判定、回收格式、依赖和验证方式。API 来源要查真实契约、分页/游标与去重；CDP 路径要观察实际 UI 和会话流程，不猜接口或选择器。
2. **选择起点并生成。** 根据目标主要职责选择 instruction-tools、code-artifact 或 business-workflow；独立选择 codex、app-server、cdp 或 custom Replay。执行 initialize 生成基础 Blueprint 与 normalize 目录。已存在文件保持不变；复用已有 manifest 的模板选择，升级不会静默覆盖项目定制。
3. **建设三段适配器。** 按[目录与协议手册](protocol.md)在 cases/、replay/、results/ 中实现；共用代码放 shared/，真实样本和断言放 tests/。将每段 manifest.stages.<stage>.status 从 needs_analysis 改为 configured 前，先补齐该段分析与实现。不得只修改状态绕过缺失能力。
4. **分段验证，再串联。** 用 run cases 生成候选；按[问题集模块](../datasets/SKILL.md)阅读、补标、反思后冻结。用一条受控任务验证 replay 的独立会话和原始回收，再用 run results 校验标准输出。真实执行和回收产物留在本项目。inspect 只报告配置和合同证据；合同通过不代表 API 权限、实际 Skill 加载或任务质量已验证。
5. **进入进化。** 先按[归因与改进方法](../evolution/analyze-and-plan.md)把实际问题、代码/轨迹证据和根因假设写进 blueprint/analysis.md，把具体修改及接受条件写进 blueprint/improvement-plan.md。由[迭代模块](../evolution/SKILL.md)按Fibonacci窗口调用项目 replay → results，新的 annotation 必须重新评价。不要直接执行整题库，或用目录/配置检查代替问题分析。

完成条件：assessment 有依据；三个入口各自有实现与样本；候选 records 合法；真实小样本能形成可追溯的执行记录；未验证或阻塞项明确可见。缺少 Harness 时仍可先完成 cases/ 并进行历史分析，不能声称已闭环。

## 其他场景

- **已有记录就是标准格式**：使用 cases/ 的 canonical-json 或 canonical-jsonl 入口，不重建另一套格式。标注缺失时由 Agent 补齐，不编造 gold answer。
- **标注平台/API/自定义导出**：在本项目 cases/ 增加取数与映射脚本，读取已有凭据配置或环境，不把凭据写入 manifest、stdout 或日志。任何清理/写入 API 不属于默认取数授权。
- **App Server 或 CDP**：模板只提供明确失败的入口；Agent 根据实际协议和页面实现并验证后才能配置为可用。CDP 脚本是按需工具，不为工作台另启常驻 Node 服务。
- **已有 tooling 或旧 Replay command**：旧配置继续运行；可让 normalize 入口调用既有项目脚本，不复制出第二套实现。新配置只有 normalization_protocol=1 才走三段管线。

## 工具与用法

工具是 [manage_project_normalization.py 使用卡](protocol.md#工具使用卡)，由安装副本执行，Python 3.9+，无第三方 Python 依赖。

```bash
RSI="$HOME/.agents/skills/rsi"
PROJECT="$HOME/.local/state/rsi/.data/projects/my_skill"
python3 "$RSI/normalize/scripts/manage_project_normalization.py" initialize --project-root "$PROJECT" --profile instruction-tools --harness codex
python3 "$RSI/normalize/scripts/manage_project_normalization.py" inspect --project-root "$PROJECT"
```

先按[项目接入](../onboarding/SKILL.md)登记源码，再初始化。命令返回 created/preserved 清单；出现未知配置、越界路径或损坏合同即失败，不覆盖既有数据。输入请求文件和输出候选的完整例子见[协议与目录手册](protocol.md)。
