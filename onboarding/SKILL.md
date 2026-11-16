# 项目接入

## 目的、交付与约束
将目标 Skill 对应源码归一化为本地 Git checkout，建立项目索引、Blueprint 和项目专属 tooling。远端地址先按用户权限 clone，再登记本地路径；不修改已安装 Skill。项目 ID 只用字母、数字、下划线和连字符。

## 主流程
1. 确认目标源码、Skill 路径、优化目标、数据源和授权边界，读取目标 AGENTS.md/开发说明，记录 Git HEAD 和 dirty 状态。
2. 写请求并执行 register。完成条件：project.json 和 SQLite 索引存在。已有同 ID 拒绝覆盖。
3. 先按[归一化脚手架模块](../normalize/SKILL.md)分析目标 Skill、数据样本和运行方式，选择场景模板与 Harness，执行 initialize；已有文件保留。完善 `blueprint/analysis.md` 的实际问题归因和 `improvement-plan.md` 的具体修改与验证条件，再配置 evaluation/replay。评分采用用户/项目确定的维度，执行前逐题标注预期效果和理想路径；不擅加通用指标或总分。按[归因与改进方法](../evolution/analyze-and-plan.md)优先修复共性根因，采用Fibonacci小窗口，不先执行整个问题库。
4. 项目数据接入、Replay 执行、原始结果转换分别放 `normalize/cases/`、`normalize/replay/`、`normalize/results/`；职责、协议和工具见[归一化模块](../normalize/SKILL.md)。已有 tooling/ 保持兼容，不重复维护；必须部署到目标环境的组件才按目标源码约定落位。
5. 按[问题集模块](../datasets/SKILL.md)继续；无 Replay 时明确未配置，不阻塞历史归因。

## 工具输入输出
register 请求：`{"op":"register","project":"my_skill","name":"My Skill","repo":"/absolute/local/repo"}`。repo 必填本地 Git 路径，name 可选展示名；输出项目元信息，写数据根不改源码。list 请求 `{"op":"list"}` 只读列项目。inspect 请求 `{"op":"inspect","project":"my_skill"}` 只读列项目文件。read 增加 `"path":"blueprint/analysis.md"` 只读 UTF-8 文件，拒绝越界及大于 4MB 的文件。

## 工具调用约定
以下命令执行安装目录内 Rust binary；`RSI` 为安装路径，`DATA` 为可写数据根，`REQUEST` 为 Agent 写好的 JSON 请求绝对路径。CLI 和 GUI 共用 dispatch，成功输出 JSON，校验失败非零退出。不要并发写同一项目。

```bash
RSI="$HOME/.agents/skills/rsi"
DATA="$HOME/.local/state/rsi/.data"
REQUEST="/tmp/rsi-request.json"
RSI_DATA_DIR="$DATA" "$RSI/local-runtime/bin/rsi-runtime" dispatch "$REQUEST"
```

工作台读取使用 `workspace` 操作，必填 project ID。输出 project、files、contents、errors；只聚合 Blueprint、normalize、tooling、datasets、sprints 中可预览文本，沿用 read 的路径与单文件 4MB 限制，总预览上限 32MB，部分读取失败以 errors 返回。它只读项目状态，不读取目标源码仓或修改记录。
