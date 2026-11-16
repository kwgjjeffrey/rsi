# 制品构建与分发

## 目的、交付与约束
从 RSI 干净源码构建带 sourceCommit、SHA-256、大小、组件版本和平台标记的制品；安装器拒绝平台不匹配。发布渠道为 skill-project.json 指定的 GitHub repository；只有上传、读回校验并公开完成后，才可宣称对应版本已发布。运行数据不分发。

## 主流程
1. 在源码仓执行 `python3 setup/scripts/manage_rsi_runtime.py build --data-dir .data`，需要 Rust/Cargo，输出当前平台二进制。执行项目测试和结构校验，再提交源码。
2. 构建归档。完成条件为 dist 中归档、manifest 和 bootstrap；验证临时安装入口，不能仅以构建成功代替验收。
3. 按当前项目授权配置真实 origin 并推送源码，再运行发布器。发布会创建 draft、上传、读回校验后公开；失败保留 draft，不能覆写已有版本。

## 工具
`build_skill_artifact.py --repo` 必填源码绝对路径，只读取已提交输入，写 dist；重复版本内容变化则拒绝。`publish_github_release.py --repo` 输入同上，需要 gh 登录、origin 与配置一致、origin/main 指向本地 HEAD，会写远端 Release 与 tag。

```bash
REPO="/absolute/path/to/rsi"
python3 "$REPO/release/scripts/build_skill_artifact.py" --repo "$REPO"
# 仅在已授权公开发布且 origin 就绪时执行：
python3 "$REPO/release/scripts/publish_github_release.py" --repo "$REPO"
```

安装者按[环境模块](../setup/SKILL.md)管理本地服务，按[安装提示词](../setup/install-skill-prompt.md)核对公开制品。发行前不得使用 latest 提示词冒充已有下载。

### npx skills 分发

公开 Release 并读回校验后，执行 `python3 release/scripts/publish_skill_repository.py --repo <源码目录> --checkout <新的临时消费仓目录>`，将同一已校验归档发布到 GitHub 的 `distribution` 分支。该分支包含可执行 runtime，不从源码目录运行。安装/更新使用 `npx skills add https://github.com/kwgjjeffrey/rsi/tree/distribution --skill rsi --global --yes`，后续通过 `npx skills check` 与 `npx skills update rsi --global --yes` 检查和更新。升级前从已安装入口停止服务，升级后从相同入口启动；数据根保持不变。
