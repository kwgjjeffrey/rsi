import type { CaseRecord, Sprint, Round } from "./model.ts";
import { score, caseTitle } from "./model.ts";
export type Verdict =
  "pass" | "fail" | "error" | "pending" | "unknown" | "missing";
export const verdictLabels: Record<Verdict, string> = {
  pass: "通过",
  fail: "未通过",
  error: "执行异常",
  pending: "待标注",
  unknown: "证据不足",
  missing: "未执行",
};
export interface MatrixCell {
  round: Round;
  record?: CaseRecord;
  verdict: Verdict;
  comparable: boolean;
}
export type Change =
  | "fixed"
  | "regressed"
  | "still-failing"
  | "unchanged"
  | "baseline"
  | "incomparable"
  | "unresolved"
  | "new";
export const changeLabels: Record<Change, string> = {
  fixed: "已修复",
  regressed: "新回归",
  "still-failing": "仍未通过",
  unchanged: "结论不变",
  baseline: "仅有基线",
  incomparable: "口径变化",
  unresolved: "待确认",
  new: "新增问题",
};
export interface MatrixRow {
  id: string;
  title: string;
  cells: MatrixCell[];
  latest?: MatrixCell;
  change: Change;
}
function explicit(value: unknown): Verdict | undefined {
  if (
    value === true ||
    value === "passed" ||
    value === "pass" ||
    value === "success"
  )
    return "pass";
  if (
    value === false ||
    value === "failed" ||
    value === "fail" ||
    value === "failure"
  )
    return "fail";
}
export function verdict(
  record: CaseRecord | undefined,
  passThreshold?: number,
): Verdict {
  if (!record) return "missing";
  if (
    ["error", "failed", "timeout", "cancelled"].includes(
      record.execution?.status,
    )
  )
    return "error";
  const a = record.annotation || {};
  if (["pending", "running"].includes(a.status)) return "pending";
  if (a.status !== "completed") return "unknown";
  const overall = explicit(a.outcome ?? a.result ?? a.verdict ?? a.passed);
  if (overall) return overall;
  const judgments = Array.isArray(a.judgments) ? a.judgments : [];
  if (
    judgments.some(
      (j) => explicit(j?.result ?? j?.value ?? j?.passed) === "fail",
    )
  )
    return "fail";
  if (
    judgments.length &&
    judgments.every(
      (j) => explicit(j?.result ?? j?.value ?? j?.passed) === "pass",
    )
  )
    return "pass";
  const n = score(record);
  if (n !== undefined) {
    if (
      typeof passThreshold === "number" &&
      Number.isFinite(passThreshold) &&
      passThreshold >= 0 &&
      passThreshold <= 100
    )
      return n >= passThreshold ? "pass" : "fail";
    if (n === 100) return "pass";
    if (n === 0) return "fail";
  }
  return "unknown";
}
function canonical(v: any): string {
  if (Array.isArray(v)) return "[" + v.map(canonical).join(",") + "]";
  if (v && typeof v === "object")
    return (
      "{" +
      Object.keys(v)
        .sort()
        .map((k) => JSON.stringify(k) + ":" + canonical(v[k]))
        .join(",") +
      "}"
    );
  return JSON.stringify(v) ?? "undefined";
}
export function comparable(a: CaseRecord, b: CaseRecord): boolean {
  return (
    !!a.annotation?.rubric_version &&
    a.annotation.rubric_version === b.annotation?.rubric_version &&
    canonical(a.task_input) === canonical(b.task_input) &&
    canonical(a.annotation.criteria) === canonical(b.annotation.criteria)
  );
}
export function matrix(
  sprint: Sprint,
  passThreshold?: number,
): { rounds: Round[]; rows: MatrixRow[] } {
  const rounds = [...sprint.rounds].sort((a, b) =>
    a.id.localeCompare(b.id, undefined, { numeric: true }),
  );
  const ids = [
    ...new Set(rounds.flatMap((r) => r.records.map((c) => c.case_id))),
  ];
  const rows = ids.map((id) => {
    const baseline = rounds
      .find((r) => Number(r.id) === 0)
      ?.records.find((c) => c.case_id === id);
    const cells = rounds.map((round) => {
      const record = round.records.find((c) => c.case_id === id);
      return {
        round,
        record,
        verdict: verdict(record, passThreshold),
        comparable:
          !!record &&
          (!baseline || record === baseline || comparable(baseline, record)),
      };
    });
    const latest = [...cells].reverse().find((c) => c.record);
    const base = cells.find((c) => Number(c.round.id) === 0);
    let change: Change = "unresolved";
    if (!baseline) change = "new";
    else if (latest === base) change = "baseline";
    else if (latest && !latest.comparable) change = "incomparable";
    else if (latest && base) {
      if (base.verdict === "fail" && latest.verdict === "pass")
        change = "fixed";
      else if (base.verdict === "pass" && latest.verdict === "fail")
        change = "regressed";
      else if (base.verdict === "fail" && latest.verdict === "fail")
        change = "still-failing";
      else if (base.verdict === "pass" && latest.verdict === "pass")
        change = "unchanged";
    }
    const first = cells.find((c) => c.record)?.record!;
    return { id, title: caseTitle(first), cells, latest, change };
  });
  return { rounds, rows };
}
