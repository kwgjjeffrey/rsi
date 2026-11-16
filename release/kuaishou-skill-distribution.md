# 将你开发的 Skill 分发给公司用户

本文供使用 awesome-skill-maker 开发目标 Skill 的开发者及其协作 Agent 使用，指导你把开发好的 Skill 交给用户安装。

## 为什么这样分发

让 Skill 分发更轻量：开发完成后，推送到公司 GitLab，就能给用户提供安装命令。开发者无需为 Skill 文件另建 CDN 项目、制作安装包、编写安装脚本或维护下载入口。

## 为什么推到 GitLab 就能安装

`kwai-skills` 已封装公司 GitLab 的地址解析、仓库拉取、Skill 发现和 Agent 安装流程。例如，`group/subgroup/repository` 会解析为 `git.corp.kuaishou.com` 上的对应仓库，用户无需手动 clone、找目录或复制 Skill 文件。

用户首次使用时安装一次 `kwai-skills`，之后即可安装不同开发者的 Skill。CLI 的安装入口直接复用下方固定命令，目标 Skill 开发者无需维护它。

用户需要公司网络、Git 和目标仓库的读取权限。这里分发的是 `SKILL.md` 及配套资源；如果你的 Skill 依赖独立程序或服务，仍需在自己的 setup 中说明如何准备这些依赖。

## 开发者需要做什么

### 1. 将开发好的 Skill 推送到公司 GitLab

仓库中保留有效的 `SKILL.md`，以及运行所需的脚本、模板等配套资源。提交并 push 到仓库默认分支，确保目标用户有仓库读取权限。

记录真实的完整仓库路径，例如 `group/subgroup/repository`。仓库只有一个 Skill 时，安装命令无需再指定 Skill 名；多个 Skill 时，按要分发的那个 Skill 的 `SKILL.md` frontmatter `name` 选择。

### 2. 生成两段可直接交给用户的命令

协作 Agent 应根据目标仓库生成下面两段命令，交付给开发者。开发者可以直接转发给用户，或放到自己的品牌官网、README、安装说明中。**交付前必须将示例仓库路径替换成目标项目的真实路径**，多 Skill 仓库也须填入真实 Skill 名。

第一段：首次安装 `kwai-skills`。已安装的用户或 Agent 可以跳过。

```sh
curl -fsSL https://cdnfile.corp.kuaishou.com/kc/files/a/omni/kwai-skills/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

第二段：安装你开发的 Skill。

```sh
kwai-skills add group/subgroup/repository -g
```

`-g` 表示安装到用户全局目录，命令会引导选择 Agent。已有 CLI 的用户只需执行第二段；Agent 可先用 `command -v kwai-skills` 检查，新 shell 需要保证 `~/.local/bin` 在 PATH 中。

多 Skill 仓库仅分发其中一个时，第二段改为：

```sh
kwai-skills add group/subgroup/repository@skill-name -g
```

`skill-name` 是仓库内 Skill 的 frontmatter `name`，用于选择 Skill，不是本地重命名。

需要 Agent 自动执行、跳过交互时，在安装命令后加 `-y`；需要限定安装给 Codex 等特定 Agent 时，再加 `-a codex`。默认交付保持上面的简短命令，多 Skill 仓库在自动执行前先明确选择目标 Skill。

### 3. 验证后交付

在隔离的用户目录或测试环境执行生成的两段命令，确认目标 Skill 及配套资源安装完整，并能由目标 Agent 发现和使用。随后将验证过的命令交给开发者，作为对外分发入口。
