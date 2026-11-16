import assert from "node:assert/strict";
import test from "node:test";
import { matrix, verdict } from "./matrix.ts";
import type { CaseRecord, Round, Sprint } from "./model.ts";
const rec = (id: string, result: string): CaseRecord => ({
  case_id: id,
  record_id: id,
  task_input: { instruction: id },
  trajectory: [],
  reflection: "evidence",
  annotation: {
    status: "completed",
    outcome: result,
    rubric_version: "v1",
    criteria: [],
  },
});
const round = (id: string, records: CaseRecord[]): Round => ({
  id,
  path: id,
  records,
  meta: {},
  reflection: "",
  plan: "",
});
const sprint = (rounds: Round[]): Sprint => ({
  id: "s1",
  meta: {},
  rounds,
  report: "",
});
test("逐题展示绿红绿，最近结果来自最后一条记录，缺测不伪造通过", () => {
  const s = sprint([
    round("000", [rec("a", "passed"), rec("b", "failed")]),
    round("001", [rec("a", "failed"), rec("b", "passed")]),
    round("002", [rec("a", "passed")]),
  ]);
  const rows = matrix(s).rows;
  assert.deepEqual(
    rows[0].cells.map((c) => c.verdict),
    ["pass", "fail", "pass"],
  );
  assert.equal(rows[1].cells[2].verdict, "missing");
  assert.equal(rows[1].latest?.round.id, "001");
  assert.equal(rows[1].change, "fixed");
  assert.equal(
    matrix(sprint(s.rounds.slice(0, 2))).rows[0].change,
    "regressed",
  );
});
test("最近执行待评价或异常，不回退展示上一轮绿灯", () => {
  const pending = rec("a", "passed");
  pending.annotation.status = "pending";
  const s = sprint([
    round("000", [rec("a", "passed")]),
    round("001", [pending]),
  ]);
  assert.equal(matrix(s).rows[0].latest?.verdict, "pending");
  pending.execution = { status: "error" };
  assert.equal(matrix(s).rows[0].latest?.verdict, "error");
});
test("改变任务或评价规则时不宣称修复或回归", () => {
  const b = rec("a", "passed");
  b.annotation.rubric_version = "v2";
  const row = matrix(
    sprint([round("000", [rec("a", "failed")]), round("001", [b])]),
  ).rows[0];
  assert.equal(row.change, "incomparable");
  assert.equal(row.latest?.verdict, "pass");
  assert.equal(row.latest?.comparable, false);
});
test("中间分数无通过阈值不擅自亮绿灯；轮次按数字排序", () => {
  const r = rec("a", "passed");
  delete r.annotation.outcome;
  r.annotation.score = 75;
  assert.equal(verdict(r), "unknown");
  assert.equal(verdict(r, 70), "pass");
  assert.equal(verdict(r, 80), "fail");
  assert.deepEqual(
    matrix(
      sprint([round("10", [r]), round("2", [r]), round("0", [r])]),
    ).rounds.map((r) => r.id),
    ["0", "2", "10"],
  );
});
test("只有基线不算优化，新问题不算修复", () => {
  const rows = matrix(
    sprint([
      round("000", [rec("a", "passed")]),
      round("001", [rec("b", "passed")]),
    ]),
  ).rows;
  assert.equal(rows[0].change, "baseline");
  assert.equal(rows[1].change, "new");
});

test("未执行题库不是实测基线，修复与首次失败比较，未来题不伪造通过", () => {
  const pending = rec("a", "passed");
  pending.annotation.status = "pending";
  const future = structuredClone(pending);
  future.case_id = "future";
  const blocked = structuredClone(pending);
  blocked.execution = { status: "error" };
  const rows = matrix(
    sprint([
      round("000", [pending, future]),
      round("001", [blocked]),
      round("002", [rec("a", "failed")]),
      round("003", [rec("a", "passed")]),
      round("004", [rec("b", "passed")]),
    ]),
  ).rows;
  const a = rows.find((r) => r.id === "a")!;
  assert.equal(a.baseline?.round.id, "002");
  assert.equal(a.change, "fixed");
  assert.equal(a.cells[4].verdict, "missing");
  assert.equal(a.latest?.round.id, "003");
  assert.equal(rows.find((r) => r.id === "future")?.latest?.verdict, "missing");
});
test("需改进是未通过，不能因为未提供综合分而显示未知", () => {
  const r = rec("a", "passed");
  delete r.annotation.outcome;
  r.annotation.judgments = [{ result: "needs_improvement" }];
  assert.equal(verdict(r), "fail");
});
