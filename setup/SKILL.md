# 环境与工作台

## 目的、交付与约束
启动仅监听 loopback 的 Rust 服务与内嵌工作台。Python 3.9+ 用于按需生命周期工具，无额外常驻 Python/Node 服务。数据根必须可写且放在不可变安装版本之外，默认示例使用用户状态目录的 `.data`。

## 使用流程
安装制品须包含当前平台的 `local-runtime/bin/rsi-runtime`。启动并打开命令返回的 URL，直接打开本地地址即可，无需登录或访问令牌。浏览器不自动读取目标源码，只读取登记项目的数据。

```bash
RSI="$HOME/.agents/skills/rsi"
DATA="$HOME/.local/state/rsi/.data"
python3 "$RSI/setup/scripts/manage_rsi_runtime.py" start --data-dir "$DATA"
python3 "$RSI/setup/scripts/manage_rsi_runtime.py" status --data-dir "$DATA"
python3 "$RSI/setup/scripts/manage_rsi_runtime.py" stop --data-dir "$DATA"
```

## 工具
`manage_rsi_runtime.py` 的 `start/status/stop` 分别启动、只读检查、终止服务；`--data-dir` 必填路径，包含 SQLite、项目文件、发现文件和日志。start 已运行时复用健康服务，失败检查 runtime.log。stop 不回滚项目文件。当前无空闲自动退出，需要显式 stop；进程异常后可 start 重启。生命周期工具以文件锁串行启停；发行升级仍需先停止服务，不能并发升级同一安装。升级前 stop，升级后 start；数据库 schema v1 当前无迁移。

安装和升级使用`manage_skill_installation.py`管理已验证 release archive/manifest，保持同一外部 store 与数据根。离线开发构建用 `python3 setup/scripts/manage_rsi_runtime.py build --data-dir .data`，需要 Rust/Cargo、Node.js 22+ 与 npm。先从 package-lock.json 准备前端构建依赖，编译 shadcn/React 工作台为单文件静态资源，再由 Cargo.lock 固定的 Rust 构建将其内嵌进二进制；运行时不需要 Node。当前只验证 macOS 主机架构，其他平台不能宣称受支持。


### 安装器调用
获得可信归档与 manifest 后，使用外部 store；归档和 manifest 路径均必填，target basename 必须为 rsi。install 校验完整性后激活稳定链接，拒绝覆盖未知目录；upgrade 从项目 GitHub Releases 固定 latest 的 tag 后下载并验证，rollback 只切换制品，不回滚数据库。

```bash
RSI="$HOME/.agents/skills/rsi"
STORE="$HOME/.local/share/rsi"
ARCHIVE="/absolute/download/rsi-0.1.0.tgz"
MANIFEST="/absolute/download/rsi-release.json"
python3 "$RSI/setup/scripts/manage_skill_installation.py" install --archive "$ARCHIVE" --manifest "$MANIFEST" --target "$RSI" --store "$STORE"
python3 "$RSI/setup/scripts/manage_skill_installation.py" check --target "$RSI"
python3 "$RSI/setup/scripts/manage_skill_installation.py" rollback --target "$RSI" --store "$STORE"
```

首次未安装时使用同一 Release 的 bootstrap，先按[安装提示词](install-skill-prompt.md)校验，不要求目标已存在。`check --target` 显示已安装版本、最新版本和可用更新；更新查询失败仅报告诊断，不阻止使用当前安装。失败保留当前安装，遇到未知目录不得自行覆盖。

### 标准安装和更新入口

使用 `npx skills add https://github.com/kwgjjeffrey/rsi/tree/distribution --skill rsi --global --yes` 安装完整消费制品。使用 `npx skills check` 检查更新，`npx skills update rsi --global --yes` 更新。该分支从校验通过的 Release 归档生成，包含 runtime；主分支保留开发源码。更新前 stop、更新后 start，继续使用同一个外部数据根。下方 archive 安装器保留作离线恢复用途。
