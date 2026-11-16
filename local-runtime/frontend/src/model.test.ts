import assert from "node:assert/strict";
import test from "node:test";
import { datasets, sprints, mean, score } from "./model.ts";
import type { Workspace, CaseRecord } from "./model.ts";
const record = (id: string, n: number, status = "completed"): CaseRecord => ({
  case_id: id,
  record_id: id,
  task_input: { instruction: "真实任务" },
  trajectory: [],
  annotation: { score: n, status },
  reflection: "基于证据的反思",
});
test("初始化、历史与Replay分开呈现，不混算分数", () => {
  const paths = {
    "datasets/current/v1/cases/a/record.json": JSON.stringify(record("a", 0)),
    "datasets/history/v1/cases/b/record.json": JSON.stringify(record("b", 30)),
    "sprints/s1/sprint.json": '{"dataset":"current"}',
    "sprints/s1/rounds/000/cases/a/record.json": JSON.stringify(record("a", 0)),
    "sprints/s1/rounds/001/cases/a/record.json": JSON.stringify(
      record("a", 100),
    ),
    "sprints/s1/rounds/001/reflection.md": "改善有证据",
  };
  const w: Workspace = {
    project: { id: "p", repo: "/repo" },
    files: Object.keys(paths).map((path) => ({ path, bytes: 1 })),
    contents: paths,
    errors: [],
  };
  assert.equal(datasets(w).length, 2);
  const sprint = sprints(w)[0];
  assert.deepEqual(
    sprint.rounds.map((r) => mean(r.records)),
    [0, 100],
  );
  assert.equal(sprint.rounds[1].reflection, "改善有证据");
  assert.equal(
    datasets(w).find((d) => d.id === "current")?.records[0].annotation.score,
    0,
  );
});
test("未知或待标注记录不显示成0分或混入均分", () => {
  assert.equal(score(record("pending", 100, "pending")), undefined);
  assert.equal(mean([record("zero", 0), record("pending", 100, "pending")]), 0);
  assert.equal(mean([record("unknown", 0, "unknown")]), undefined);
});

test("异常执行与越界分数不能被展示为有效得分", () => {
  const failed = record("failure", 100);
  failed.execution = { status: "error" };
  assert.equal(score(failed), undefined);
  assert.equal(score(record("invalid", 101)), undefined);
  assert.equal(score(record("invalid", -1)), undefined);
});

test("归档Sprint不重复列为任务，Round读取冻结的选题信息", () => {
  const paths = {
    "sprints/old/sprint.json": '{"archived_into":"daily"}',
    "sprints/old/rounds/001/cases/a/record.json": JSON.stringify(
      record("a", 0),
    ),
    "sprints/daily/sprint.json": '{"title":"Daily"}',
    "sprints/daily/rounds/002/selection.json": '{"repair":true,"cases":["a"]}',
    "sprints/daily/rounds/002/cases/a/record.json": JSON.stringify(
      record("a", 100),
    ),
  };
  const w: Workspace = {
    project: { id: "p", repo: "/repo" },
    files: Object.keys(paths).map((path) => ({ path, bytes: 1 })),
    contents: paths,
    errors: [],
  };
  assert.deepEqual(
    sprints(w).map((s) => s.id),
    ["daily"],
  );
  assert.deepEqual(sprints(w)[0].rounds[0].meta.cases, ["a"]);
  assert.equal(sprints(w)[0].rounds[0].meta.repair, true);
});
