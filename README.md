# RSI

Skill 驱动的目标 Skill 持续优化工作台。统一 case record：task input、trajectory、annotation、reflection。每个 Round 汇总逐题归因，保留代码和评测证据。

消费入口 [SKILL.md](SKILL.md)。源码与制品：[GitHub / rsi](https://github.com/kwgjjeffrey/rsi) · [Releases](https://github.com/kwgjjeffrey/rsi/releases)。消费方从 Release 下载归档、manifest 和 bootstrap，校验后安装至 `~/.agents/skills/rsi`；运行时不引用开发 checkout。安装步骤见 [安装说明](setup/install-skill-prompt.md)。当前发行目标仅为 macOS Apple Silicon（darwin-arm64）。

Skill、Rust runtime 和 GUI 组件分别记录版本。`check --target` 检查安装与可用更新；用户可执行 `upgrade` 或 `rollback`，版本目录之外的数据不会被覆盖。

开发：`python3 setup/scripts/manage_rsi_runtime.py build --data-dir .data`，然后 `python3 setup/scripts/manage_rsi_runtime.py start --data-dir .data`。开发需要 Rust/Cargo、Node.js 22+、npm 和 Python 3.9+。状态 .data 不进入 Git；安装后使用版本目录之外的数据根。

已实现和限制见 [设计](docs/design.md)。

工作台使用 shadcn/ui + React，单文件内嵌进 Rust 服务；源码位于 local-runtime/frontend。开发构建会按 package-lock.json 准备依赖，发行运行无需 Node。
