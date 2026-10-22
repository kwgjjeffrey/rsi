export type Json = Record<string, any>;
export interface Project {
  id: string;
  name?: string;
  repo: string;
  coverage?: string;
  replay_status?: string;
}
export interface FileEntry {
  path: string;
  bytes: number;
}
export interface Workspace {
  project: Project;
  files: FileEntry[];
  contents: Record<string, string>;
  errors: string[];
}
export interface CaseRecord {
  schema_version?: number;
  case_id: string;
  record_id: string;
  task_input: any;
  trajectory: any[];
  annotation: Json;
  reflection: string;
  execution?: Json;
}
export interface Dataset {
  key: string;
  id: string;
  version: string;
  records: CaseRecord[];
}
export interface Round {
  id: string;
  path: string;
  records: CaseRecord[];
  meta: Json;
  reflection: string;
  plan: string;
  comparison?: Json;
}
export interface Sprint {
  id: string;
  meta: Json;
  rounds: Round[];
  report: string;
}
export async function api<T>(request: Json): Promise<T> {
  const response = await fetch("/api", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal: AbortSignal.timeout(15000),
  });
  const raw = await response.text();
  let value;
  try {
    value = JSON.parse(raw);
  } catch {
    throw Error(`服务返回异常（HTTP ${response.status}）`);
  }
  if (!response.ok) throw Error(value.error || `HTTP ${response.status}`);
  return value;
}
export async function loadWorkspace(project: string): Promise<Workspace> {
  return api<Workspace>({ op: "workspace", project });
}
export function parse<T = Json>(text: string | undefined, fallback: T): T {
  try {
    return text ? JSON.parse(text) : fallback;
  } catch {
    return fallback;
  }
}
export function recordsAt(w: Workspace, prefix: string): CaseRecord[] {
  return Object.entries(w.contents)
    .filter(
      ([p]) => p.startsWith(prefix + "/cases/") && p.endsWith("/record.json"),
    )
    .map(([, s]) => parse<CaseRecord | null>(s, null))
    .filter((c): c is CaseRecord => !!c && typeof c.case_id === "string")
    .sort((a, b) => a.case_id.localeCompare(b.case_id));
}
export function datasets(w: Workspace): Dataset[] {
  const keys = [
    ...new Set(
      w.files
        .map((f) =>
          f.path
            .match(/^datasets\/([^/]+)\/([^/]+)\//)
            ?.slice(1)
            .join("/"),
        )
        .filter((v): v is string => !!v),
    ),
  ];
  return keys.map((key) => ({
    key,
    id: key.split("/")[0],
    version: key.split("/")[1],
    records: recordsAt(w, "datasets/" + key),
  }));
}
export function sprints(w: Workspace): Sprint[] {
  const ids = [
    ...new Set(
      w.files
        .map((f) => f.path.match(/^sprints\/([^/]+)\//)?.[1])
        .filter((v): v is string => !!v),
    ),
  ];
  return ids
    .map((id) => {
      const prefix = "sprints/" + id;
      const rounds = [
        ...new Set(
          w.files
            .map(
              (f) =>
                f.path.match(
                  new RegExp("^sprints/" + id + "/rounds/([^/]+)/"),
                )?.[1],
            )
            .filter((v): v is string => !!v),
        ),
      ]
        .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
        .map((n) => {
          const p = prefix + "/rounds/" + n;
          return {
            id: n,
            path: p,
            records: recordsAt(w, p),
            meta: parse<Json>(w.contents[p + "/round.json"], {}),
            reflection: w.contents[p + "/reflection.md"] || "",
            plan: w.contents[p + "/plan.md"] || "",
            comparison: parse(w.contents[p + "/comparison.json"], undefined),
          };
        });
      return {
        id,
        meta: parse<Json>(w.contents[prefix + "/sprint.json"], {}),
        rounds,
        report: w.contents[prefix + "/report.md"] || "",
      };
    })
    .sort((a, b) => b.id.localeCompare(a.id));
}
export function score(c: CaseRecord): number | undefined {
  const n = c.annotation?.score;
  return c.annotation?.status === "completed" &&
    c.execution?.status !== "error" &&
    Number.isFinite(n) &&
    typeof n === "number" &&
    n >= 0 &&
    n <= 100
    ? n
    : undefined;
}
export function mean(cs: CaseRecord[]): number | undefined {
  const ns = cs.map(score).filter((n): n is number => n !== undefined);
  return ns.length
    ? Math.round(ns.reduce((a, b) => a + b, 0) / ns.length)
    : undefined;
}
export function caseTitle(c: CaseRecord) {
  return (
    c.task_input?.title ||
    c.task_input?.instruction?.split(/[。\n]/)[0]?.slice(0, 65) ||
    c.case_id.replace(/[_-]/g, " ")
  );
}
export function sprintTitle(s: Sprint) {
  return s.meta.title || s.id.replace(/[_-]/g, " ");
}
export function datasetTitle(d: Dataset) {
  return d.id.replace(/[_-]/g, " ");
}
export function statusText(c: CaseRecord) {
  return c.execution?.status === "error"
    ? "执行异常"
    : c.annotation?.status === "completed"
      ? "已标注"
      : c.annotation?.status === "pending"
        ? "待标注"
        : "证据不足";
}
export function text(value: any): string {
  if (value == null) return "未记录";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(text).join("、");
  return Object.entries(value)
    .map(([k, v]) => `${k}：${text(v)}`)
    .join("\n");
}
