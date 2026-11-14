# 从 GitHub Release 安装 RSI

源码和制品仓库：https://github.com/kwgjjeffrey/rsi 。只使用该仓库公开 Release 的归档、manifest 和 bootstrap；不要通过复制开发 checkout 安装。

需要 macOS Apple Silicon、Python 3.9+、curl 和 OpenSSL/HTTPS 信任链；不需要 Rust、Node 或 npm。运行状态在版本目录之外。

1. 读取 GitHub API 的 `https://api.github.com/repos/kwgjjeffrey/rsi/releases/latest`，固定返回的 `tag_name`（格式 vX.Y.Z）。后续下载都使用该 tag，不能重复解析 latest 混用版本。
2. 从同一个 tag 下载 `rsi-X.Y.Z.tgz`、`rsi-release.json`、`bootstrap_skill_installation.py`。下载地址为 `https://github.com/kwgjjeffrey/rsi/releases/download/<tag>/<filename>`。也可使用已登录的 gh CLI 下载同一个已固定 tag。
3. 校验 manifest 的 name、version、repository、sourceCommit、platform，以及归档和 bootstrap 的 SHA-256/size。sourceCommit 应与该 tag 的 commit 一致；来源必须是上述受信任仓库。
4. 从下载目录执行 bootstrap（不是源码目录）：

```sh
python3 bootstrap_skill_installation.py --archive rsi-X.Y.Z.tgz --manifest rsi-release.json --target "$HOME/.agents/skills/rsi" --store "$HOME/.local/share/rsi"
```

5. 从安装位置检查并启动：

```sh
RSI="$HOME/.agents/skills/rsi"
python3 "$RSI/setup/scripts/manage_skill_installation.py" check --target "$RSI"
python3 "$RSI/setup/scripts/manage_rsi_runtime.py" start --data-dir "$HOME/.local/state/rsi/.data"
```

升级由用户触发，沿用相同 target/store：

```sh
python3 "$HOME/.agents/skills/rsi/setup/scripts/manage_skill_installation.py" upgrade --repository kwgjjeffrey/rsi --target "$HOME/.agents/skills/rsi" --store "$HOME/.local/share/rsi"
```

更新不会启动项目 Replay。发布者确认的平台、组件版本和源码 SHA 均以该 Release manifest 为准。
