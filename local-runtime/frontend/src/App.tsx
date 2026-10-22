import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Bot,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleDot,
  ClipboardCopy,
  Code2,
  Database,
  FileCode2,
  FileText,
  Folder,
  FolderOpen,
  GitBranch,
  Layers3,
  LayoutDashboard,
  ListChecks,
  Loader2,
  MessageSquare,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Terminal,
  Workflow,
  X,
} from "lucide-react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
  EmptyMedia,
} from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  api,
  loadWorkspace,
  datasets,
  sprints,
  mean,
  score,
  caseTitle,
  sprintTitle,
  datasetTitle,
  statusText,
  text,
  parse,
} from "./model";
import type {
  Workspace,
  Project,
  CaseRecord,
  Sprint,
  Round,
  Dataset,
  Json,
} from "./model";

const views = [
  { id: "overview", label: "项目概览", icon: LayoutDashboard },
  { id: "blueprint", label: "Blueprint", icon: BookOpen },
  { id: "datasets", label: "问题集", icon: Database },
  { id: "iterations", label: "迭代观察", icon: Workflow },
] as const;
type View = (typeof views)[number]["id"];
function Md({ children }: { children: string }) {
  return (
    <div className="markdown">
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) =>
            href?.startsWith("http") ? (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
              </a>
            ) : (
              <span title={href}>{children}</span>
            ),
        }}
      >
        {children}
      </Markdown>
    </div>
  );
}
function Blank({ title, description }: { title: string; description: string }) {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Layers3 />
        </EmptyMedia>
        <EmptyTitle>{title}</EmptyTitle>
        <EmptyDescription>{description}</EmptyDescription>
      </EmptyHeader>
    </Empty>
  );
}
function Section({
  title,
  description,
  children,
  action,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <CardTitle>{title}</CardTitle>
            {description && <CardDescription>{description}</CardDescription>}
          </div>
          {action}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
function Score({ value }: { value: number | undefined }) {
  return (
    <span className="score-value">
      {value ?? "—"}
      {value !== undefined && <small>/100</small>}
    </span>
  );
}
function RawButton({ onClick }: { onClick: () => void }) {
  return (
    <Button variant="ghost" size="sm" onClick={onClick}>
      <Code2 data-icon="inline-start" />
      原始数据
    </Button>
  );
}
function Facts({ values }: { values: [string, any][] }) {
  return (
    <dl className="facts">
      {values.map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd>{text(v)}</dd>
        </div>
      ))}
    </dl>
  );
}
function HumanValue({ value }: { value: any }) {
  if (value == null)
    return <span className="text-muted-foreground">未记录</span>;
  if (typeof value === "string") return <Md>{value}</Md>;
  if (typeof value !== "object") return <span>{String(value)}</span>;
  if (Array.isArray(value))
    return (
      <div className="flex flex-col gap-3">
        {value.map((v, i) => (
          <div key={i} className="rounded-lg border p-3">
            <HumanValue value={v} />
          </div>
        ))}
      </div>
    );
  return (
    <div className="flex flex-col gap-4">
      {Object.entries(value).map(([k, v]) => (
        <div key={k} className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">
            {fieldNames[k] || k}
          </span>
          <HumanValue value={v} />
        </div>
      ))}
    </div>
  );
}
const fieldNames: Record<string, string> = {
  instruction: "任务描述",
  source_scope: "来源与适用范围",
  criteria: "评价标准",
  version: "规则版本",
  weight: "权重",
  id: "标识",
  expectation: "预期行为",
  scale: "评分范围",
  command: "执行命令",
  fresh_session: "独立会话",
  scope: "适用范围",
  max_rounds: "轮次上限",
  runtime: "运行服务",
  skill: "Skill",
  gui: "工作台",
  status: "状态",
  inputs: "输入文件",
  context: "上下文",
  reason: "依据",
  source: "来源",
};
function CaseSummary({
  record,
  onClick,
  active = false,
}: {
  record: CaseRecord;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button className={cn("case-row", active && "selected")} onClick={onClick}>
      <div className="flex min-w-0 items-start gap-3">
        <div className="case-icon">
          <ListChecks className="size-4" />
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <span className="font-medium leading-relaxed">
            {caseTitle(record)}
          </span>
          <span className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
            {record.task_input?.instruction || record.case_id}
          </span>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{statusText(record)}</Badge>
            <span className="font-mono text-[11px] text-muted-foreground">
              {record.case_id}
            </span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Score value={score(record)} />
          <ChevronRight className="size-4 text-muted-foreground" />
        </div>
      </div>
    </button>
  );
}
function Trajectory({ record }: { record: CaseRecord }) {
  const events = (record.trajectory || []).filter(
    (e) =>
      e.type !== "item.started" &&
      e.type !== "turn.started" &&
      e.type !== "thread.started",
  );
  return (
    <div className="flex flex-col gap-5">
      <Facts
        values={[
          [
            "独立会话",
            record.execution?.session_id ||
              record.trajectory?.find((e) => e.thread_id)?.thread_id ||
              "历史材料，未提供会话 ID",
          ],
          [
            "记录来源",
            record.trajectory?.some((e) => e.type === "secondary_evidence")
              ? "二手评审，非完整原始轨迹"
              : "执行事件记录",
          ],
        ]}
      />
      <Separator />
      {!events.length ? (
        <Blank
          title="没有可展示的执行轨迹"
          description="轨迹尚未回收；不能据此判断任务成功。"
        />
      ) : (
        <div className="timeline">
          {events.map((event, index) => {
            const item = event.item || event;
            const kind = item.type;
            const command = kind === "command_execution";
            const message = kind === "agent_message";
            const source =
              kind === "secondary_evidence" || kind === "source_excerpt";
            if (event.type === "turn.completed")
              return (
                <div key={index} className="timeline-end">
                  <CheckCheck className="size-4" />
                  会话结束
                  {event.usage?.output_tokens
                    ? ` · 输出 ${event.usage.output_tokens} tokens`
                    : ""}
                </div>
              );
            return (
              <div className="timeline-event" key={index}>
                <div className="timeline-dot">
                  {command ? (
                    <Terminal className="size-3.5" />
                  ) : message ? (
                    <Bot className="size-3.5" />
                  ) : source ? (
                    <FileText className="size-3.5" />
                  ) : (
                    <CircleDot className="size-3.5" />
                  )}
                </div>
                {command ? (
                  <Collapsible className="tool-event">
                    <CollapsibleTrigger className="flex w-full items-center justify-between gap-3 text-left">
                      <span className="flex min-w-0 flex-col gap-1">
                        <span className="text-xs text-muted-foreground">
                          工具调用 ·{" "}
                          {item.exit_code === 0
                            ? "成功"
                            : item.exit_code == null
                              ? "未完成"
                              : "失败"}
                        </span>
                        <code className="break-all text-xs">
                          {item.command}
                        </code>
                      </span>
                      <ChevronDown className="size-4 shrink-0" />
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <Separator className="my-4" />
                      <div className="tool-output">
                        {item.aggregated_output ? (
                          <Md>{item.aggregated_output}</Md>
                        ) : (
                          <p className="text-muted-foreground">无文本输出</p>
                        )}
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                ) : message ? (
                  <div className="message-event">
                    <div className="mb-3 text-xs text-muted-foreground">
                      Agent
                    </div>
                    <Md>{item.text || ""}</Md>
                  </div>
                ) : source ? (
                  <Section title="来源证据" description={item.source}>
                    <Md>{item.text || ""}</Md>
                  </Section>
                ) : (
                  <div className="tool-event">
                    <span className="mb-2 block text-xs text-muted-foreground">
                      {kind === "error" ? "Harness 提示" : kind || event.type}
                    </span>
                    <p className="whitespace-pre-wrap text-sm">
                      {item.message || item.text || text(item)}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
function CaseDetail({
  record,
  onBack,
  onRaw,
}: {
  record: CaseRecord;
  onBack: () => void;
  onRaw: (v: any, title?: string) => void;
}) {
  const a = record.annotation || {};
  const criteria = a.criteria || [];
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft data-icon="inline-start" />
          返回问题列表
        </Button>
        <RawButton onClick={() => onRaw(record, "Case 原始记录")} />
      </div>
      <div className="flex items-start justify-between gap-5">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{statusText(record)}</Badge>
            <span className="font-mono text-xs text-muted-foreground">
              {record.case_id}
            </span>
          </div>
          <h2 className="text-xl font-semibold tracking-tight">
            {caseTitle(record)}
          </h2>
        </div>
        <Score value={score(record)} />
      </div>
      <Tabs defaultValue="annotation">
        <TabsList variant="line">
          <TabsTrigger value="input">任务输入</TabsTrigger>
          <TabsTrigger value="trace">
            执行轨迹{" "}
            <Badge variant="secondary">
              {record.trajectory?.filter(
                (e) =>
                  e.type === "item.completed" ||
                  e.type === "secondary_evidence",
              ).length ||
                record.trajectory?.length ||
                0}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="annotation">评价标注</TabsTrigger>
          <TabsTrigger value="reflection">逐题反思</TabsTrigger>
        </TabsList>
        <TabsContent value="input" className="pt-5">
          <Section
            title="任务输入"
            description="初始化与 Replay 使用同一份任务输入。"
          >
            <HumanValue value={record.task_input} />
          </Section>
        </TabsContent>
        <TabsContent value="trace" className="pt-5">
          <Trajectory record={record} />
        </TabsContent>
        <TabsContent value="annotation" className="pt-5">
          <div className="flex flex-col gap-5">
            <Section
              title="评价结果"
              description="查看评分依据，而不只看一个总分。"
            >
              <Facts
                values={[
                  ["评价规则", a.rubric_version],
                  ["标注者", a.annotator?.type || a.annotator],
                  [
                    "置信度",
                    typeof a.confidence === "number"
                      ? Math.round(a.confidence * 100) + "%"
                      : "未记录",
                  ],
                  ["证据范围", a.scope || a.source_type || "本次执行轨迹"],
                ]}
              />
            </Section>
            <div className="flex flex-col gap-3">
              {(a.judgments || []).map((j: Json, i: number) => {
                const criterion = criteria.find(
                  (c: Json) => c.id === (j.criterion || j.criterion_id),
                );
                return (
                  <Card key={i}>
                    <CardHeader>
                      <div className="flex items-center justify-between gap-4">
                        <CardTitle>
                          {criterion?.expectation ||
                            j.criterion ||
                            j.criterion_id ||
                            `判断 ${i + 1}`}
                        </CardTitle>
                        <Badge
                          variant={
                            j.result === "failed" ? "destructive" : "secondary"
                          }
                        >
                          {j.score != null
                            ? `${j.score} 分`
                            : j.result === "failed"
                              ? "未通过"
                              : j.result || j.value || "已评价"}
                        </Badge>
                      </div>
                      <CardDescription>
                        {j.reason || j.explanation || "依据如下"}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="evidence">
                        <FileText className="size-4 shrink-0" />
                        <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                          {text(j.evidence || "未附证据")}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
            {a.reason && (
              <Alert>
                <CircleDot />
                <AlertTitle>评价说明</AlertTitle>
                <AlertDescription>{a.reason}</AlertDescription>
              </Alert>
            )}
          </div>
        </TabsContent>
        <TabsContent value="reflection" className="pt-5">
          <Section
            title="逐题反思"
            description="具体证据、原因假设与改进方向；本轮整体反思会引用这些结论。"
          >
            {record.reflection ? (
              <Md>{record.reflection}</Md>
            ) : (
              <Blank
                title="反思尚未生成"
                description="评价完成后，由 Agent 阅读轨迹并补齐逐题归因。"
              />
            )}
          </Section>
        </TabsContent>
      </Tabs>
    </div>
  );
}
function Stat({
  label,
  value,
  description,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  description: string;
  icon: typeof Activity;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardDescription>{label}</CardDescription>
          <Icon className="size-4 text-muted-foreground" />
        </div>
        <CardTitle className="text-3xl tabular-nums">{value}</CardTitle>
      </CardHeader>
      <CardFooter>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardFooter>
    </Card>
  );
}
function Overview({
  workspace,
  onNavigate,
  onSprint,
}: {
  workspace: Workspace;
  onNavigate: (v: View) => void;
  onSprint: (id: string) => void;
}) {
  const ds = datasets(workspace),
    ss = sprints(workspace);
  const rounds = ss.flatMap((s) => s.rounds).filter((r) => r.id !== "000");
  return (
    <div className="page-content">
      <div className="page-heading">
        <div>
          <div className="eyebrow">PROJECT OVERVIEW</div>
          <h1>项目进化概览</h1>
          <p>观察问题、执行与反思，判断目标 Skill 是否真正变好。</p>
        </div>
        <Badge variant="outline">
          <GitBranch data-icon="inline-start" />
          本地源码
        </Badge>
      </div>
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <Stat
          label="问题集版本"
          value={ds.length}
          description="初始化记录独立保存"
          icon={Database}
        />
        <Stat
          label="已收录问题"
          value={ds.reduce((n, d) => n + d.records.length, 0)}
          description="包含历史证据与当前执行"
          icon={ListChecks}
        />
        <Stat
          label="进化任务"
          value={ss.length}
          description="每个 Sprint 冻结独立基线"
          icon={Workflow}
        />
        <Stat
          label="代码优化轮次"
          value={rounds.length}
          description={
            rounds.length ? "不含初始化 Round 0" : "尚未进入修改与重放阶段"
          }
          icon={GitBranch}
        />
      </div>
      {!rounds.length && (
        <Alert>
          <CircleDot />
          <AlertTitle>当前处于基线观察阶段，尚未发生代码优化</AlertTitle>
          <AlertDescription>
            已完成项目接入、历史材料归一化和一次独立会话验证。Round 0
            是初始化记录，不代表完成了一轮进化，也没有可报告的提升幅度。
          </AlertDescription>
        </Alert>
      )}
      <div className="grid items-start gap-5 xl:grid-cols-[1.5fr_1fr]">
        <Section
          title="进化任务"
          description="从任务进入轮次，查看证据和整体反思。"
          action={
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate("iterations")}
            >
              全部任务
              <ArrowRight data-icon="inline-end" />
            </Button>
          }
        >
          <div className="flex flex-col gap-3">
            {ss.map((s) => (
              <button
                key={s.id}
                className="sprint-overview"
                onClick={() => onSprint(s.id)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-col gap-1.5">
                    <span className="font-medium">{sprintTitle(s)}</span>
                    <span className="text-xs text-muted-foreground">
                      {s.id}
                    </span>
                  </div>
                  <Badge variant="secondary">
                    {s.rounds.some((r) => r.id !== "000")
                      ? "迭代中"
                      : "Round 0 · 基线"}
                  </Badge>
                </div>
                <div className="mt-5 flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    {s.rounds.reduce((n, r) => n + r.records.length, 0)} 条记录
                    · {s.rounds.length} 个轮次
                  </span>
                  <span className="flex items-center gap-1">
                    查看任务
                    <ArrowRight className="size-3.5" />
                  </span>
                </div>
              </button>
            ))}
          </div>
        </Section>
        <div className="flex flex-col gap-5">
          <Section
            title="当前 Blueprint"
            description="这个项目如何分析、评价和重放。"
          >
            <div className="flex flex-col gap-4">
              {[
                ["分析策略", "blueprint/analysis.md"],
                ["评价规则", "blueprint/evaluation.json"],
                ["重放适配", "blueprint/replay.json"],
              ].map(([label, p]) => (
                <div
                  key={p}
                  className="flex items-center justify-between gap-3"
                >
                  <span className="text-sm">{label}</span>
                  <Badge
                    variant={workspace.contents[p] ? "secondary" : "outline"}
                  >
                    {workspace.contents[p] ? "已配置" : "待配置"}
                  </Badge>
                </div>
              ))}
              <Separator />
              <Button variant="outline" onClick={() => onNavigate("blueprint")}>
                查看策略与工具
                <ArrowRight data-icon="inline-end" />
              </Button>
            </div>
          </Section>
          <div className="source-note">
            <FolderOpen className="size-4 shrink-0" />
            <div>
              <p className="mb-1 text-xs font-medium">目标源码</p>
              <p className="break-all font-mono text-xs leading-relaxed text-muted-foreground">
                {workspace.project.repo}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
function RoundView({
  sprint,
  round,
  onRaw,
}: {
  sprint: Sprint;
  round: Round;
  onRaw: (v: any, title?: string) => void;
}) {
  const [selected, setSelected] = useState<string>();
  const [tab, setTab] = useState("cases");
  useEffect(() => {
    setSelected(undefined);
    setTab("cases");
  }, [sprint.id, round.id]);
  const record = round.records.find((c) => c.case_id === selected);
  if (record)
    return (
      <CaseDetail
        record={record}
        onBack={() => setSelected(undefined)}
        onRaw={onRaw}
      />
    );
  const comparison = round.comparison;
  const baseline = round.id === "000";
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-3 gap-4">
        <div className="round-stat">
          <span>本轮记录</span>
          <strong>
            {round.records.length}
            <small> 个问题</small>
          </strong>
        </div>
        <div className="round-stat">
          <span>已完成标注</span>
          <strong>
            {
              round.records.filter((c) => c.annotation?.status === "completed")
                .length
            }
            <small> / {round.records.length}</small>
          </strong>
        </div>
        <div className="round-stat">
          <span>{baseline ? "基线均分" : "本轮均分"}</span>
          <Score value={mean(round.records)} />
        </div>
      </div>
      {baseline && (
        <div className="inline-note">
          <CircleDot className="size-4 shrink-0" />
          <p>
            Round 0 是初始化快照。这里的分数描述原始记录，不代表代码改进效果。
          </p>
        </div>
      )}
      {comparison && (
        <Section
          title="相对 Round 0"
          description={`共 ${comparison.total} 题，其中 ${comparison.comparable} 题可比；不可比项单列。`}
        >
          <div className="grid grid-cols-2 gap-4">
            {[
              ["基线", comparison.baseline_mean],
              ["本轮", comparison.round_mean],
            ].map(([label, n]) => (
              <div className="flex flex-col gap-2" key={String(label)}>
                <span className="text-sm">{label}</span>
                <Score value={typeof n === "number" ? n : undefined} />
                <Progress value={typeof n === "number" ? n : 0} />
              </div>
            ))}
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            {Object.entries(comparison.groups || {}).map(([key, values]) => (
              <Badge variant="outline" key={key}>
                {
                  (
                    {
                      improved: "改善",
                      regressed: "回归",
                      unchanged: "不变",
                      incomparable: "不可比",
                    } as Json
                  )[key]
                }{" "}
                {Array.isArray(values) ? values.length : 0}
              </Badge>
            ))}
          </div>
        </Section>
      )}
      <Tabs value={tab} onValueChange={(v) => setTab(String(v))}>
        <TabsList variant="line">
          <TabsTrigger value="cases">
            逐题记录 <Badge variant="secondary">{round.records.length}</Badge>
          </TabsTrigger>
          <TabsTrigger value="reflection">整体反思</TabsTrigger>
          <TabsTrigger value="plan">
            {baseline ? "初始化与源码" : "改进计划"}
          </TabsTrigger>
          <TabsTrigger value="report">任务报告</TabsTrigger>
        </TabsList>
        <TabsContent value="cases" className="pt-5">
          <Card>
            <CardHeader>
              <CardTitle>问题与执行结果</CardTitle>
              <CardDescription>
                点击问题查看任务输入、执行轨迹、评价依据和逐题反思。
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {round.records.length ? (
                round.records.map((c) => (
                  <CaseSummary
                    key={c.case_id}
                    record={c}
                    onClick={() => setSelected(c.case_id)}
                  />
                ))
              ) : (
                <Blank
                  title="尚无执行记录"
                  description="本轮 Replay 完成后，真实结果将显示在这里。"
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="reflection" className="pt-5">
          <Section
            title="本轮整体反思"
            description="汇总逐题 reflection，并按需结合源码和轨迹分析共性原因。"
          >
            {round.reflection ? (
              <Md>{round.reflection}</Md>
            ) : (
              <Blank
                title="整体反思尚未生成"
                description="阅读各问题的反思之后，再形成这一轮的整体判断。"
              />
            )}
          </Section>
        </TabsContent>
        <TabsContent value="plan" className="pt-5">
          {baseline ? (
            <Section
              title="初始化条件"
              description="本次 Sprint 使用的固定问题集与源码信息。"
            >
              <Facts
                values={[
                  ["问题集", sprint.meta.dataset],
                  ["数据版本", sprint.meta.version],
                  ["源码版本", sprint.meta.source?.revision],
                  ["轮次预算", sprint.meta.budget?.max_rounds],
                  ["未提交修改", sprint.meta.source?.dirty || "未记录"],
                ]}
              />
            </Section>
          ) : (
            <Section
              title="本轮改进计划"
              description="执行前落盘，允许开发者查看和介入。"
            >
              {round.plan ? (
                <Md>{round.plan}</Md>
              ) : (
                <Blank
                  title="计划尚未记录"
                  description="改代码前应明确改进假设、验证方式和停止条件。"
                />
              )}
            </Section>
          )}
        </TabsContent>
        <TabsContent value="report" className="pt-5">
          <Section title="任务报告">
            {sprint.report ? (
              <Md>{sprint.report}</Md>
            ) : (
              <Blank
                title="尚无汇总报告"
                description="可以先查看逐题记录和本轮整体反思。"
              />
            )}
          </Section>
        </TabsContent>
      </Tabs>
    </div>
  );
}
function Iterations({
  workspace,
  initialSprint,
  onRaw,
}: {
  workspace: Workspace;
  initialSprint?: string;
  onRaw: (v: any, title?: string) => void;
}) {
  const ss = useMemo(() => sprints(workspace), [workspace]);
  const [id, setId] = useState(initialSprint || ss[0]?.id);
  const [roundId, setRoundId] = useState("000");
  const sprint = ss.find((s) => s.id === id) || ss[0];
  const round =
    sprint?.rounds.find((r) => r.id === roundId) || sprint?.rounds[0];
  if (!sprint)
    return (
      <Blank
        title="还没有进化任务"
        description="先准备问题集并冻结一个 Sprint 基线。"
      />
    );
  return (
    <div className="split-view">
      <aside className="context-pane">
        <div className="context-title">
          <span>进化任务</span>
          <Badge variant="outline">{ss.length}</Badge>
        </div>
        <div className="flex flex-col gap-2">
          {ss.map((s) => (
            <button
              key={s.id}
              className={cn("context-item", s.id === sprint.id && "selected")}
              onClick={() => {
                setId(s.id);
                setRoundId(s.rounds[0]?.id || "000");
              }}
            >
              <Workflow className="size-4 shrink-0" />
              <span className="flex flex-col gap-2">
                <span className="text-sm font-medium">{sprintTitle(s)}</span>
                <span className="text-xs text-muted-foreground">
                  {s.rounds.length} 个轮次 ·{" "}
                  {s.rounds.reduce((n, r) => n + r.records.length, 0)} 条记录
                </span>
              </span>
            </button>
          ))}
        </div>
        <div className="mt-auto pt-8 text-xs leading-relaxed text-muted-foreground">
          每个任务独立冻结问题集与 Blueprint。不同任务的分数不混在一起比较。
        </div>
      </aside>
      <div className="detail-pane">
        <div className="page-heading">
          <div>
            <div className="eyebrow">SPRINT / {sprint.id}</div>
            <h1>{sprintTitle(sprint)}</h1>
            <p>按轮观察改进计划、执行结果与归因。</p>
          </div>
          <RawButton onClick={() => onRaw(sprint.meta, "Sprint 原始配置")} />
        </div>
        <div className="round-picker">
          {sprint.rounds.map((r) => (
            <Button
              key={r.id}
              variant={r.id === round?.id ? "secondary" : "ghost"}
              onClick={() => setRoundId(r.id)}
            >
              <CircleDot data-icon="inline-start" />
              Round {Number(r.id)}
              {r.id === "000" && <Badge variant="outline">基线</Badge>}
            </Button>
          ))}
        </div>
        {round && (
          <RoundView
            key={sprint.id + round.id}
            sprint={sprint}
            round={round}
            onRaw={onRaw}
          />
        )}
      </div>
    </div>
  );
}
function Datasets({
  workspace,
  onRaw,
  onImport,
}: {
  workspace: Workspace;
  onRaw: (v: any, title?: string) => void;
  onImport: () => void;
}) {
  const ds = useMemo(() => datasets(workspace), [workspace]);
  const [key, setKey] = useState(ds[0]?.key);
  const [caseId, setCaseId] = useState<string>();
  const [query, setQuery] = useState("");
  const dataset = ds.find((d) => d.key === key) || ds[0];
  const record = dataset?.records.find((c) => c.case_id === caseId);
  const filteredRecords =
    dataset?.records.filter((c) =>
      (caseTitle(c) + text(c.task_input) + c.case_id)
        .toLowerCase()
        .includes(query.toLowerCase()),
    ) || [];
  if (!dataset)
    return (
      <Blank
        title="还没有问题集"
        description="点击新增问题集，复制提示词交给 Agent 完成导入与打标。"
      />
    );
  return (
    <div className="split-view">
      <aside className="context-pane">
        <div className="context-title">
          <span>问题集版本</span>
          <Badge variant="outline">{ds.length}</Badge>
        </div>
        <div className="flex flex-col gap-2">
          {ds.map((d) => (
            <button
              key={d.key}
              className={cn(
                "context-item",
                dataset.key === d.key && "selected",
              )}
              onClick={() => {
                setKey(d.key);
                setCaseId(undefined);
              }}
            >
              <Database className="size-4 shrink-0" />
              <span className="flex flex-col gap-2">
                <span className="text-sm font-medium">{datasetTitle(d)}</span>
                <span className="text-xs text-muted-foreground">
                  {d.version} · {d.records.length} 个问题
                </span>
              </span>
            </button>
          ))}
        </div>
        <Button variant="outline" className="mt-6" onClick={onImport}>
          <Plus data-icon="inline-start" />
          新增问题集
        </Button>
        <div className="mt-auto pt-8 text-xs leading-relaxed text-muted-foreground">
          问题集保存初始化记录。后续 Replay 结果保存在对应轮次，不覆盖这里。
        </div>
      </aside>
      <div className="detail-pane">
        {record ? (
          <CaseDetail
            record={record}
            onBack={() => setCaseId(undefined)}
            onRaw={onRaw}
          />
        ) : (
          <>
            <div className="page-heading">
              <div>
                <div className="eyebrow">DATASET / {dataset.id}</div>
                <h1>{datasetTitle(dataset)}</h1>
                <p>每个问题包含输入、轨迹、标注与反思。</p>
              </div>
              <Badge variant="outline">{dataset.version} · 已冻结</Badge>
            </div>
            <div className="mb-5 flex items-center gap-4">
              <div className="relative max-w-sm flex-1">
                <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
                <Input
                  aria-label="搜索问题"
                  className="pl-9"
                  placeholder="搜索问题、任务描述…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <span className="text-xs text-muted-foreground">
                {dataset.records.length} 个问题
              </span>
            </div>
            <Card>
              <CardHeader>
                <CardTitle>问题列表</CardTitle>
                <CardDescription>
                  人工标注与 Agent 标注保留各自来源和判断依据。
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                {filteredRecords.map((c) => (
                  <CaseSummary
                    key={c.case_id}
                    record={c}
                    onClick={() => setCaseId(c.case_id)}
                  />
                ))}
                {!filteredRecords.length && (
                  <Blank
                    title="没有匹配的问题"
                    description="调整搜索词，或切换到其他问题集版本。"
                  />
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
interface TreeNode {
  name: string;
  path: string;
  children: TreeNode[];
  file?: boolean;
}
function tree(paths: string[]) {
  const root: TreeNode = { name: "", path: "", children: [] };
  for (const path of paths) {
    let node = root;
    const parts = path.split("/");
    parts.forEach((name, i) => {
      let child = node.children.find((n) => n.name === name);
      if (!child) {
        child = {
          name,
          path: parts.slice(0, i + 1).join("/"),
          children: [],
          file: i === parts.length - 1,
        };
        node.children.push(child);
      }
      node = child;
    });
  }
  function sort(n: TreeNode) {
    n.children.sort(
      (a, b) =>
        Number(!!a.file) - Number(!!b.file) || a.name.localeCompare(b.name),
    );
    n.children.forEach(sort);
  }
  sort(root);
  return root.children;
}
function TreeItem({
  node,
  selected,
  onSelect,
  depth = 0,
}: {
  node: TreeNode;
  selected: string;
  onSelect: (p: string) => void;
  depth?: number;
}) {
  const [open, setOpen] = useState(true);
  if (node.file)
    return (
      <button
        className={cn("tree-file", selected === node.path && "selected")}
        style={{ paddingLeft: 12 + depth * 16 }}
        onClick={() => onSelect(node.path)}
      >
        <FileText className="size-4 shrink-0" />
        <span className="truncate">{node.name}</span>
      </button>
    );
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger
        className="tree-folder"
        style={{ paddingLeft: 12 + depth * 16 }}
      >
        {open ? (
          <ChevronDown className="size-3.5" />
        ) : (
          <ChevronRight className="size-3.5" />
        )}
        {open ? (
          <FolderOpen className="size-4" />
        ) : (
          <Folder className="size-4" />
        )}
        <span>{node.name}</span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        {node.children.map((c) => (
          <TreeItem
            key={c.path}
            node={c}
            selected={selected}
            onSelect={onSelect}
            depth={depth + 1}
          />
        ))}
      </CollapsibleContent>
    </Collapsible>
  );
}
function Blueprint({
  workspace,
  onRaw,
}: {
  workspace: Workspace;
  onRaw: (v: any, title?: string) => void;
}) {
  const files = workspace.files.filter((f) =>
    /^(blueprint|tooling)\//.test(f.path),
  );
  const [selected, setSelected] = useState(
    files.some((f) => f.path === "blueprint/analysis.md")
      ? "blueprint/analysis.md"
      : files[0]?.path || "",
  );
  const content = workspace.contents[selected];
  const labels: Record<string, string> = {
    "overview.md": "项目目标与范围",
    "analysis.md": "分析策略",
    "constraints.md": "约束与停止条件",
    "evaluation.json": "评价规则",
    "replay.json": "Replay 配置",
  };
  return (
    <div className="split-view">
      <aside className="context-pane">
        <div className="context-title">
          <span>策略与脚手架</span>
          <Badge variant="outline">只读</Badge>
        </div>
        <div className="file-tree">
          {tree(files.map((f) => f.path)).map((node) => (
            <TreeItem
              key={node.path}
              node={node}
              selected={selected}
              onSelect={setSelected}
            />
          ))}
        </div>
        <div className="mt-auto pt-8 text-xs leading-relaxed text-muted-foreground">
          这是当前项目的 Blueprint。迭代使用的冻结版本，保存在各 Sprint 快照中。
        </div>
      </aside>
      <div className="detail-pane">
        <div className="page-heading">
          <div>
            <div className="eyebrow">BLUEPRINT</div>
            <h1>
              {labels[selected.split("/").pop() || ""] ||
                selected.split("/").pop() ||
                "项目策略"}
            </h1>
            <p className="font-mono text-xs">{selected}</p>
          </div>
          <RawButton
            onClick={() =>
              onRaw(
                selected.endsWith(".json") ? parse(content, {}) : content,
                "文件原文",
              )
            }
          />
        </div>
        {content === undefined ? (
          <Blank
            title="文件无法预览"
            description="文件未加载或超过读取限制，请检查项目文件。"
          />
        ) : selected.endsWith(".md") ? (
          <div className="document-paper">
            <Md>{content}</Md>
          </div>
        ) : selected.endsWith(".json") ? (
          <Section
            title={labels[selected.split("/").pop() || ""] || "配置内容"}
            description="以可读字段展示；原始 JSON 可通过右上角查看。"
          >
            <HumanValue value={parse(content, {})} />
          </Section>
        ) : (
          <Section
            title="项目专属脚手架"
            description="只读源码预览；工作台不会执行此文件。"
          >
            <pre className="code-block">{content}</pre>
          </Section>
        )}
      </div>
    </div>
  );
}
export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [workspace, setWorkspace] = useState<Workspace>();
  const [view, setView] = useState<View>("overview");
  const [sprintId, setSprintId] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [dialog, setDialog] = useState<{
    title: string;
    body: string;
    prompt?: boolean;
  }>();
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    let cancelled = false;
    api<Project[]>({ op: "list" })
      .then((ps) => {
        if (cancelled) return;
        setProjects(ps);
        setProjectId((id) =>
          ps.some((p) => p.id === id) ? id : ps[0]?.id || "",
        );
        if (!ps.length) setLoading(false);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(String(e));
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [revision]);
  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    setLoading(true);
    setError("");
    loadWorkspace(projectId)
      .then((w) => {
        if (!cancelled) {
          setWorkspace(w);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(String(e));
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, revision]);
  function raw(v: any, title = "原始数据") {
    setCopied(false);
    setDialog({
      title,
      body: typeof v === "string" ? v : JSON.stringify(v, null, 2),
    });
  }
  function prompt(kind: "project" | "dataset") {
    setCopied(false);
    setDialog({
      title: kind === "project" ? "接入新项目" : "新增问题集",
      prompt: true,
      body:
        kind === "project"
          ? "请使用 RSI 的 onboarding/SKILL.md 接入目标 Skill。确认本地 Git 源码路径、Skill 路径、数据源和优化目标，建立 Blueprint 与项目专属工具。数据根由 RSI_DATA_DIR 或启动命令的 --data-dir 指定。缺少真实 Replay 时明确记录未配置，不伪造执行结果。"
          : `请使用 RSI 的 datasets/SKILL.md 为项目 ${projectId} 导入新的问题集版本。确认数据源，保留原始来源，将每条记录归一化为 task_input、trajectory、annotation、reflection；没有人工标注时阅读真实轨迹完成标注。版本冻结后不要覆盖，Replay 写到对应 Round。`,
    });
  }
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Workflow className="size-5" />
          </div>
          <div>
            <strong>RSI</strong>
            <span>Skill 进化工作台</span>
          </div>
          <Badge variant="outline">LOCAL</Badge>
        </div>
        <Separator />
        <div className="project-switch">
          <span className="eyebrow">目标项目</span>
          <Select
            value={projectId}
            onValueChange={(v) => {
              if (v) {
                setProjectId(String(v));
                setSprintId(undefined);
              }
            }}
          >
            <SelectTrigger className="w-full" aria-label="切换目标项目">
              <SelectValue placeholder="选择项目" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {projects.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name || p.id}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          <Button variant="ghost" size="sm" onClick={() => prompt("project")}>
            <Plus data-icon="inline-start" />
            接入新项目
          </Button>
        </div>
        <nav className="flex flex-col gap-1.5 px-3">
          {views.map((item) => (
            <Button
              key={item.id}
              variant={view === item.id ? "secondary" : "ghost"}
              className="justify-start"
              onClick={() => setView(item.id)}
            >
              <item.icon data-icon="inline-start" />
              {item.label}
              {view === item.id && (
                <span className="ml-auto">
                  <ChevronRight className="size-3.5" />
                </span>
              )}
            </Button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="flex items-center gap-2 text-xs">
            <span className={cn("connection-dot", error && "disconnected")} />
            {error ? "连接异常" : "本地服务已连接"}
          </div>
          <p>
            数据留在本机
            <br />
            每个结论，都能回到证据
          </p>
        </div>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <div className="flex min-w-0 items-center gap-2 text-sm">
            <span className="text-muted-foreground">工作台</span>
            <ChevronRight className="size-3.5 text-muted-foreground" />
            <span className="truncate font-medium">
              {projects.find((p) => p.id === projectId)?.name ||
                projectId ||
                "项目"}
            </span>
            <span className="mx-1 text-muted-foreground">/</span>
            <span>{views.find((v) => v.id === view)?.label}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              disabled={loading}
              onClick={() => setRevision((n) => n + 1)}
            >
              {loading ? (
                <Loader2 className="animate-spin" data-icon="inline-start" />
              ) : (
                <RefreshCw data-icon="inline-start" />
              )}
              刷新
            </Button>
            <Separator orientation="vertical" className="h-5" />
            <Button
              size="sm"
              variant="outline"
              onClick={() => prompt("dataset")}
            >
              <Plus data-icon="inline-start" />
              新增问题集
            </Button>
          </div>
        </header>
        {error ? (
          <div className="page-content">
            <Alert variant="destructive">
              <CircleDot />
              <AlertTitle>无法连接本地工作台</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => setRevision((n) => n + 1)}
            >
              重新连接
            </Button>
          </div>
        ) : loading ? (
          <div className="page-content flex flex-col gap-5">
            <Skeleton className="h-10 w-64" />
            <Skeleton className="h-5 w-96" />
            <div className="grid grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-32" />
              ))}
            </div>
            <Skeleton className="h-80" />
          </div>
        ) : workspace ? (
          <>
            {workspace.errors.length > 0 && (
              <Alert variant="destructive">
                <AlertTitle>部分文件未加载</AlertTitle>
                <AlertDescription>
                  {workspace.errors.join("\n")}
                </AlertDescription>
              </Alert>
            )}
            {view === "overview" && (
              <Overview
                workspace={workspace}
                onNavigate={setView}
                onSprint={(id) => {
                  setSprintId(id);
                  setView("iterations");
                }}
              />
            )}
            {view === "iterations" && (
              <Iterations
                key={workspace.project.id + String(sprintId)}
                workspace={workspace}
                initialSprint={sprintId}
                onRaw={raw}
              />
            )}{" "}
            {view === "datasets" && (
              <Datasets
                key={workspace.project.id}
                workspace={workspace}
                onRaw={raw}
                onImport={() => prompt("dataset")}
              />
            )}{" "}
            {view === "blueprint" && (
              <Blueprint
                key={workspace.project.id}
                workspace={workspace}
                onRaw={raw}
              />
            )}
          </>
        ) : (
          <Blank
            title="接入第一个目标项目"
            description="通过左侧接入新项目，复制提示词交给 Agent 完成登记。"
          />
        )}
      </main>
      <Dialog
        open={!!dialog}
        onOpenChange={(open) => {
          if (!open) setDialog(undefined);
        }}
      >
        <DialogContent className="max-h-[85vh] overflow-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>{dialog?.title}</DialogTitle>
            <DialogDescription>
              {dialog?.prompt
                ? "复制这段提示词，交给 Agent 执行。当前按钮只生成说明，不修改数据。"
                : "保留完整原始内容，供核对与追溯。日常观察请使用结构化视图。"}
            </DialogDescription>
          </DialogHeader>
          <pre className="code-block max-h-[55vh]">{dialog?.body}</pre>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(undefined)}>
              关闭
            </Button>
            <Button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(dialog?.body || "");
                  setCopied(true);
                } catch {
                  setCopied(false);
                }
              }}
            >
              {copied ? (
                <Check data-icon="inline-start" />
              ) : (
                <ClipboardCopy data-icon="inline-start" />
              )}
              {copied ? "已复制" : "复制内容"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
