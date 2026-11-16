# 归一化目录与协议 v1

## 项目目录

```text
<project>/
  blueprint/                 # 项目目标、分析与评价策略、运行约束
  normalize/
    README.md                # 目录职责和数据流
    assessment.md            # Agent 根据目标 Skill 做出的接入分析
    manifest.json            # 模板来源、协议版本、阶段配置
    cases/normalize_cases.py # 取数与工作记录映射
    replay/run_replay.py     # Harness 执行与原始回收；CDP 起点为 run_replay.mjs
    results/normalize_results.py # 原始结果到标准输出
    shared/io_helpers.py     # 项目脚本共用的协议与路径辅助
    tests/                   # 适配器样本和断言，不是业务问题集
    receipts/                # 工具生成的合同证据
  datasets/                  # 冻结的初始化 case records
  sprints/<id>/rounds/<n>/cases/<case_id>/
    raw/                     # 本次执行的原始回收及转换证据
    record.json              # 同构 Replay case record
```

normalize 中的额外脚本、候选和私有样本均留在本项目。目标 Skill 发布时不携带这些项目状态；RSI 发布只带模板和通用工具，不携带 `.data`。

## 三段协议

所有入口 stdin 接收 JSON 对象，stdout 只返回一个 JSON 对象；错误非零退出。共享字段为 protocol_version=1、project_root（由 RSI 注入）。脚本从项目根运行，解释器只选 python3 或 node；entrypoint 及 dependencies 是 normalize/ 内相对路径。

**cases**：请求 source 是项目定义的数据源描述。默认入口支持 kind=file，path 为文件路径，format 为 canonical-json（默认）或 canonical-jsonl。自定义 API/CSV/对话导出由 Agent 在项目入口中实现映射。返回 `{"protocol_version":1,"records":[...]}`；每个 record 包含 case_id、record_id、task_input、trajectory、annotation、reflection。允许额外项目字段，不丢弃原有扩展数据；重复 case_id、非法类型或不完整 completed 标注会被拒绝。缺标的记录可以用 pending/unknown，但仍需由 Agent 阅读、补标再作为可评价基线。

**replay**：请求包含 case_id、task_input、source.repo/revision、fresh_session、run_dir、可选 timeout_seconds；不得携带 annotation/reflection/reference/gold_answer。默认 codex 入口仅只读探测，执行 codex exec 创建新会话，不 resume，忽略用户配置以避免无关服务；更广泛的权限或其他 Harness 必须在项目评估中明确。source 必须指向已登记 repo；run_dir 必须留在本 RSI 项目中，且默认 Codex 模板拒绝覆盖已存在运行目录。

Replay 返回原始结果信封：protocol_version=1、status=completed|error。项目自行约定 format、原始文件引用及元数据。默认 Codex 格式 codex-events-jsonl 包含 events_path（相对项目根）、skill_digest、isolation_evidence；error 要有原因。App Server/CDP 的原始信封由项目实现，不能假装是 Codex 事件。

**results**：请求 raw_result 是原始信封，replay_request 是本次公开执行请求。项目入口解析本 Harness 的返回，输出：

```json
{"protocol_version":1,"trajectory":[],"execution":{"status":"completed","session_id":"真实会话ID","loaded_skill_digest":"实际来源指纹"}}
```

失败输出 execution.status=error 和 error 字符串，不要求伪造会话 ID。results 不能输出 task_input、annotation 或 reflection。成功时必须有会话 ID、指纹；这只校验协议，实际是否加载目标 Skill 要通过轨迹另行核对。默认模板明确把源码摘要标成 source snapshot，不能当加载验证已通过。

RSI 最后保留原 task_input/case_id/initial_record_id，以及冻结的 criteria/rubric_version/reference 和项目扩展契约，设置 annotation.status=pending、reflection=""，组装同构 record。旧 score/outcome/judgments/reason/evidence 等观察结论清空；评价上下文不传给被测会话。

## 逐项评价

项目可以只用分类评价，不要求总分。已完成的 annotation 必须有 rubric_version、非空逐题 reflection，并完整覆盖冻结 criteria：

```json
{"status":"completed","rubric_version":"project-v1","criteria":[{"id":"project_defined_dimension"}],"judgments":[{"criterion":"project_defined_dimension","result":"passed","reason":"Explain the observed behavior and why it meets this criterion.","evidence":[{"source":"relative/path/to/actual-trajectory.json"}]}]}
```

result 为 passed、failed 或 needs_improvement，criterion 不能重复或缺失。执行异常、未知结果和未完成评价不能作为通过结论。窗口门禁还要求逐项 reason/evidence 与本轮反思；它验证结构，不验证分析推理是否正确。只有项目明确选择数值评价时才提供 score，并配置资格阈值；RSI 不据此擅加评分维度。

## manifest

manifest 的 protocol_version=1，template_version 是模板版本，profile/harness 记录选择。stages.cases/replay/results 各含 runtime、entrypoint、status（needs_analysis 或 configured）；可选 dependencies 是本阶段额外项目代码路径数组。共用 shared/*.py 自动纳入合同证据指纹。入口、配置、共享代码或 dependencies 变化后旧合同回执失效；移植项目或重新配置后重新验证。

## 工具使用卡

`manage_project_normalization.py` 必填 action 和 --project-root（已登记项目的绝对路径）。

| action | 其他输入 | 输出与修改 |
|---|---|---|
| initialize | --profile 三种场景之一，默认 instruction-tools；--harness codex/app-server/cdp/custom，默认 custom | 创建缺失模板和 manifest；返回 created/preserved；不覆盖现有文件、不改源码/冻结数据 |
| inspect | 无 | 只读返回阶段配置、入口存在与合同回执有效性，不启动 Harness 或取数 |
| run | --stage cases/replay/results、--request JSON 路径、--output 项目内新路径；可选 --timeout 正整数秒，默认600 | 调用项目入口，校验输出，写候选及合同回执；实际取数/执行范围由该项目入口与授权决定 |
| validate | --stage cases/results、--request 待校验 JSON 路径 | 只读校验标准合同，不执行项目脚本、不证明真实集成 |

run 输出路径已存在则拒绝覆盖；超时终止该入口及其子进程组；输入/协议错误非零退出，默认不把项目 stderr 或原始数据打印到工具输出。需要诊断入口时，在本机项目目录直接执行该入口查看错误，不将私有材料复制到公开反馈。

完整例子（先完成 assessment、实现并将 cases 状态配置为 configured）：

```bash
RSI="$HOME/.agents/skills/rsi"
PROJECT="$HOME/.local/state/rsi/.data/projects/my_skill"
SOURCE="/absolute/path/to/canonical-records.json"
mkdir -p "$PROJECT/normalize/requests" "$PROJECT/normalize/candidates"
python3 - "$SOURCE" "$PROJECT/normalize/requests/cases.json" <<'PY'
import json, sys
from pathlib import Path
Path(sys.argv[2]).write_text(json.dumps({"source":{"kind":"file","path":sys.argv[1],"format":"canonical-json"}}))
PY
python3 "$RSI/normalize/scripts/manage_project_normalization.py" run --project-root "$PROJECT" --stage cases --request "$PROJECT/normalize/requests/cases.json" --output "$PROJECT/normalize/candidates/cases-v001.json"
python3 "$RSI/normalize/scripts/manage_project_normalization.py" validate --project-root "$PROJECT" --stage cases --request "$PROJECT/normalize/candidates/cases-v001.json"
```

转换后按[问题集流程](../datasets/SKILL.md)补标、逐题反思再导入；本工具不会自动将候选晋升为冻结问题集。完整 Replay 使用[迭代命令](../evolution/SKILL.md)，不要手写另一套轮次保存工具。
