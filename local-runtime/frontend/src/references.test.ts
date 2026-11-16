import assert from "node:assert/strict";
import test from "node:test";
import { resolveReference, referenceParts } from "./references.ts";

test("absolute evaluation references and Markdown relative links resolve to the same project file", () => {
  assert.equal(
    resolveReference(
      "/data/projects/p/blueprint/analysis.md",
      "/data/projects/p",
    ),
    "blueprint/analysis.md",
  );
  assert.equal(
    resolveReference(
      "../analysis.md#L12",
      "/data/projects/p",
      "blueprint/contracts/example.md",
    ),
    "blueprint/analysis.md",
  );
  assert.equal(
    resolveReference(
      "blueprint/analysis.md:12",
      "/data/projects/p",
      "sprints/s1/report.md",
    ),
    "blueprint/analysis.md",
  );
  assert.equal(
    resolveReference(
      "./scoring%20notes.md",
      "/data/projects/p",
      "blueprint/analysis.md",
    ),
    "blueprint/scoring notes.md",
  );
});
test("references never re-map another project's absolute paths or escape the project", () => {
  for (const value of [
    "/data/projects/p2/private.md",
    "../../private.md",
    "https://example.com/a.md",
    "javascript:alert(1)",
    "file:///etc/passwd",
    "%ZZ",
  ])
    assert.equal(resolveReference(value, "/data/projects/p"), undefined);
  assert.equal(
    resolveReference(
      "../../../outside.md",
      "/data/projects/p",
      "blueprint/a.md",
    ),
    undefined,
  );
});
test("multiple citation paths remain distinct, with surrounding explanation preserved", () => {
  const text =
    "依据 /data/projects/p/sprints/s1/reflection.md，另见 blueprint/evaluation.json；无需执行脚本。";
  const parts = referenceParts(text, "/data/projects/p");
  assert.equal(parts.map((x) => x.text).join(""), text);
  assert.deepEqual(
    parts.filter((x) => x.path).map((x) => x.path),
    ["sprints/s1/reflection.md", "blueprint/evaluation.json"],
  );
});
