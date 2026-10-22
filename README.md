# RSI

Skill 驱动的目标 Skill 持续优化工作台。统一 case record：task input、trajectory、annotation、reflection。每个 Round 汇总逐题归因，保留代码和评测证据。

消费入口 [SKILL.md](SKILL.md)。源码仓库：[GitLab / omni / rsi](https://git.corp.kuaishou.com/ks-ep/ea-zonghe/omni/rsi)。当前为开发版本，尚未发布可安装的 Release。仅本机 macOS 构建经过验证，不能把源码脚手架当成公开安装制品。

开发：`python3 setup/scripts/manage_rsi_runtime.py build --data-dir .data`，然后 `python3 setup/scripts/manage_rsi_runtime.py start --data-dir .data`。开发需要 Rust/Cargo、Node.js 22+、npm 和 Python 3.9+。状态 .data 不进入 Git；安装后使用版本目录之外的数据根。

已实现和限制见 [设计](docs/design.md)。

工作台使用 shadcn/ui + React，单文件内嵌进 Rust 服务；源码位于 local-runtime/frontend。开发构建会按 package-lock.json 准备依赖，发行运行无需 Node。
