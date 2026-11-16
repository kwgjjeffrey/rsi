import { useMemo, useState } from "react";
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock3,
  MinusCircle,
  HelpCircle,
  Search,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import {
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableCaption,
} from "@/components/ui/table";
import { matrix, verdictLabels, changeLabels, verdict } from "./matrix";
import type { MatrixCell, Verdict } from "./matrix";
import type { Sprint } from "./model";
import { score } from "./model";
const icons = {
  pass: CheckCircle2,
  fail: XCircle,
  error: AlertCircle,
  pending: Clock3,
  missing: MinusCircle,
  unknown: HelpCircle,
};
export function OutcomeCell({
  cell,
  onOpen,
  title,
  latest = false,
}: {
  cell?: MatrixCell;
  onOpen: (cell: MatrixCell) => void;
  title: string;
  latest?: boolean;
}) {
  const status = cell?.verdict || "missing";
  const Icon = icons[status];
  const n = cell?.record ? score(cell.record) : undefined;
  return (
    <button
      className="outcome-cell"
      data-verdict={status}
      aria-label={`${title} · ${latest ? "最近结果 · " : ""}Round ${cell ? Number(cell.round.id) : "—"} · ${verdictLabels[status]}`}
      disabled={!cell?.record}
      onClick={() => cell && onOpen(cell)}
    >
      <span className="verdict-pill">
        <Icon className="size-3.5" />
        {verdictLabels[status]}
      </span>
      <span className="cell-meta">
        {n !== undefined ? `${n} 分` : "—"}
        {latest && cell ? ` · Round ${Number(cell.round.id)}` : ""}
      </span>
      {cell?.record && !cell.comparable && (
        <span className="cell-warning">与基线口径不同</span>
      )}
    </button>
  );
}
export default function RoundMatrix({
  sprint,
  threshold,
  onOpen,
  onRound,
}: {
  sprint: Sprint;
  threshold?: number;
  onOpen: (cell: MatrixCell) => void;
  onRound: (id: string) => void;
}) {
  const data = useMemo(() => matrix(sprint, threshold), [sprint, threshold]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const shown = data.rows.filter(
    (row) =>
      (row.title + row.id).toLowerCase().includes(query.toLowerCase()) &&
      (filter === "all" ||
        (filter === "regressed" && row.change === "regressed") ||
        (filter === "problems" && row.latest?.verdict !== "pass")),
  );
  const optimized = data.rounds.filter((r) => Number(r.id) !== 0).length;
  const latestPass = data.rows.filter(
    (r) => r.latest?.verdict === "pass",
  ).length;
  return (
    <div className="flex flex-col gap-5">
      <div className="matrix-summary">
        <Card>
          <CardHeader>
            <CardDescription>已记录轮次</CardDescription>
            <CardTitle>
              {data.rounds.length}{" "}
              <span className="metric-unit">
                含初始化 · 评估与修复 {optimized} 轮
              </span>
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>最近逐题结果</CardDescription>
            <CardTitle>
              {latestPass}{" "}
              <span className="metric-unit">/ {data.rows.length} 通过</span>
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>相对各题首次实测</CardDescription>
            <CardTitle>
              <span className="trend-fixed">
                {data.rows.filter((r) => r.change === "fixed").length} 修复
              </span>
              <span className="metric-unit"> / </span>
              <span className="trend-regressed">
                {data.rows.filter((r) => r.change === "regressed").length} 回归
              </span>
            </CardTitle>
          </CardHeader>
        </Card>
      </div>
      {optimized === 0 && (
        <div className="inline-note">
          <HelpCircle className="size-4 shrink-0" />
          <p>
            真实数据目前只有 <strong>Round 0（基线）</strong>，还没有 Round
            1。后续重放记录产生后，会在下方自动追加轮次列；不会把基线当作一次优化。
          </p>
        </div>
      )}
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex flex-col gap-2">
              <CardTitle>问题 × 轮次 · 结论对比矩阵</CardTitle>
              <CardDescription>
                横向看同一问题如何变化。点击灯号查看对应执行的标注、轨迹和反思。
              </CardDescription>
            </div>
            <div className="matrix-legend">
              {(
                [
                  "pass",
                  "fail",
                  "error",
                  "pending",
                  "unknown",
                  "missing",
                ] as Verdict[]
              ).map((status) => {
                const Icon = icons[status];
                return (
                  <span key={status} data-verdict={status}>
                    <Icon className="size-3" />
                    {verdictLabels[status]}
                  </span>
                );
              })}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="matrix-controls">
            <div className="relative min-w-0 flex-1">
              <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
              <Input
                className="pl-9"
                aria-label="搜索矩阵问题"
                placeholder="搜索问题或 case ID…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <Select
              value={filter}
              onValueChange={(v) => setFilter(String(v || "all"))}
            >
              <SelectTrigger aria-label="筛选矩阵结果">
                <SelectValue>
                  {
                    (
                      {
                        all: "全部问题",
                        problems: "只看未通过 / 待确认",
                        regressed: "只看新回归",
                      } as Record<string, string>
                    )[filter]
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="all">全部问题</SelectItem>
                  <SelectItem value="problems">只看未通过 / 待确认</SelectItem>
                  <SelectItem value="regressed">只看新回归</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
          <div className="conclusion-matrix">
            <Table>
              <TableCaption>
                Round 0 可为未执行的问题库，修复 /
                回归相对各题首次有效实测；后续未选中的题显示“未执行”，不复制旧结果。最近结果
                =
                每题最近一次有记录的结论（包括异常和待标注）；缺测显示“未执行”。口径变化时保留本轮灯号，但不计为修复或回归。中间分数需明确通过阈值；没有阈值时，仅满分
                / 零分或明确结论亮绿 / 红灯。
              </TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead className="case-column">问题</TableHead>
                  <TableHead className="latest-column">
                    <div>最近结果</div>
                    <small>逐题最近一次有记录</small>
                  </TableHead>
                  {data.rounds.map((r) => (
                    <TableHead key={r.id}>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onRound(r.id)}
                      >
                        Round {Number(r.id)}
                        {Number(r.id) === 0 && (
                          <Badge variant="outline">基线</Badge>
                        )}
                        <ArrowRight data-icon="inline-end" />
                      </Button>
                      {Array.isArray(r.meta.cases) && (
                        <small>
                          {r.meta.repair ? "修复复测" : "新增采样"} ·{" "}
                          {r.meta.cases.length} 题
                        </small>
                      )}
                      <small>
                        {
                          r.records.filter(
                            (c) => verdict(c, threshold) === "pass",
                          ).length
                        }{" "}
                        通过 / {r.records.length} 记录
                      </small>
                    </TableHead>
                  ))}
                  <TableHead>相对首次实测变化</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shown.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="case-column">
                      <div className="matrix-case-title">{row.title}</div>
                      <div className="matrix-case-id">{row.id}</div>
                    </TableCell>
                    <TableCell className="latest-column">
                      <OutcomeCell
                        cell={row.latest}
                        latest
                        title={row.title}
                        onOpen={onOpen}
                      />
                    </TableCell>
                    {row.cells.map((cell) => (
                      <TableCell key={cell.round.id}>
                        <OutcomeCell
                          cell={cell}
                          title={row.title}
                          onOpen={onOpen}
                        />
                      </TableCell>
                    ))}
                    <TableCell>
                      <Badge variant="outline" data-change={row.change}>
                        {changeLabels[row.change]}
                      </Badge>
                      {row.baseline && (
                        <div className="text-xs text-muted-foreground">
                          首次实测 Round {Number(row.baseline.round.id)}
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {!shown.length && (
                  <TableRow>
                    <TableCell colSpan={data.rounds.length + 3}>
                      <div className="py-12 text-center text-sm text-muted-foreground">
                        没有匹配的问题；可以调整搜索或筛选条件。
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
