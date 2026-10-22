# RSI 安装状态

源码仓库：https://git.corp.kuaishou.com/ks-ep/ea-zonghe/omni/rsi

当前没有已发布的可安装 Release。不要访问模板遗留的 GitHub 仓库或宣称自动升级已可用。

开发者从 GitLab 克隆源码后，按根 README.md 构建并启动本地 runtime。构建需要 Rust/Cargo、Node.js 22+、npm 和 Python 3.9+。构建与临时验证放 `.trial/`；正式项目状态放 `.data/`，均不提交 Git。

后续发布需先确定 GitLab 制品分发渠道，再提供对应的校验及安装流程。skill-project.json 中 repository 字段由旧 GitHub 制品工具使用，sourceRepository 才是当前源码地址。
