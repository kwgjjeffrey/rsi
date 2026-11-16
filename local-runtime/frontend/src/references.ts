/** Resolve evidence only inside the registered project's data directory. */
export function resolveReference(
  reference: string,
  root: string | undefined,
  basePath?: string,
): string | undefined {
  let value: string;
  try {
    value = decodeURIComponent(reference.trim());
  } catch {
    return;
  }
  value = value.replace(/(?:#L\d+(?:-L?\d+)?|:\d+(?::\d+)?)$/, "");
  if (!value || /^[a-z][a-z\d+.-]*:/i.test(value) || value.includes("\\"))
    return;
  if (value.startsWith("/")) {
    if (!root || !value.startsWith(root.replace(/\/$/, "") + "/")) return;
    value = value.slice(root.replace(/\/$/, "").length + 1);
  } else if (
    basePath &&
    !/^(blueprint|normalize|tooling|datasets|sprints)\//.test(value)
  ) {
    value = basePath.slice(0, basePath.lastIndexOf("/") + 1) + value;
  }
  const parts: string[] = [];
  for (const part of value.split("/")) {
    if (!part || part === ".") continue;
    if (part === "..") {
      if (!parts.length) return;
      parts.pop();
    } else parts.push(part);
  }
  return parts.length ? parts.join("/") : undefined;
}

export function referenceParts(value: string, root?: string) {
  const pattern =
    /(?:\/[^\s<>"'`,，]+|(?:blueprint|normalize|tooling|datasets|sprints)\/[^\s<>"'`,，]+)\.(?:md|json|jsonl|txt|py|mjs|js|ts|tsx|yaml|yml|patch)(?::\d+)?/g;
  const parts: { text: string; path?: string }[] = [];
  let at = 0;
  for (const match of value.matchAll(pattern)) {
    const start = match.index!;
    if (start > at) parts.push({ text: value.slice(at, start) });
    parts.push({ text: match[0], path: resolveReference(match[0], root) });
    at = start + match[0].length;
  }
  if (at < value.length) parts.push({ text: value.slice(at) });
  return parts;
}
