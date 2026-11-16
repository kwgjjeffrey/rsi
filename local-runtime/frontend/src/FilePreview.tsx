import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { api } from "./model";
import type { Workspace } from "./model";
import { resolveReference, referenceParts } from "./references";

export const EvidenceWorkspace = createContext<Workspace | undefined>(
  undefined,
);

export function Md({
  children,
  basePath,
}: {
  children: string;
  basePath?: string;
}) {
  return (
    <div className="markdown">
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) =>
            href?.startsWith("https://") || href?.startsWith("http://") ? (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
              </a>
            ) : (
              <FileReference reference={href || ""} basePath={basePath}>
                {children}
              </FileReference>
            ),
        }}
      >
        {children}
      </Markdown>
    </div>
  );
}

function FileReference({
  reference,
  basePath,
  children,
}: {
  reference: string;
  basePath?: string;
  children?: ReactNode;
}) {
  const workspace = useContext(EvidenceWorkspace);
  const path = resolveReference(reference, workspace?.root, basePath);
  const [open, setOpen] = useState(false),
    [content, setContent] = useState<string>(),
    [error, setError] = useState("");
  useEffect(() => {
    if (!open || !workspace || !path) return;
    let active = true;
    setContent(undefined);
    setError("");
    api<{ content: string }>({
      op: "read",
      project: workspace.project.id,
      path,
    })
      .then((result) => {
        if (active) setContent(result.content);
      })
      .catch((reason) => {
        if (active) setError(String(reason));
      });
    return () => {
      active = false;
    };
  }, [open, path, workspace?.project.id]);
  if (!workspace || !path)
    return (
      <span title="引用不在当前项目中，无法在工作台预览">
        {children || reference}
      </span>
    );
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button
            variant="link"
            className="h-auto max-w-full justify-start whitespace-normal px-0 text-left"
            title={reference}
          />
        }
      >
        <FileText data-icon="inline-start" />
        <span className="min-w-0 break-all">{children || path}</span>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] overflow-auto sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>引用预览 · {path.split("/").pop()}</DialogTitle>
          <DialogDescription className="break-all">{path}</DialogDescription>
        </DialogHeader>
        {error ? (
          <Alert variant="destructive">
            <AlertTitle>无法读取引用</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : content === undefined ? (
          <div role="status" className="flex items-center gap-2">
            <Loader2 className="size-4 animate-spin" />
            正在读取文件…
          </div>
        ) : path.endsWith(".md") ? (
          <Md basePath={path}>{content}</Md>
        ) : (
          <pre className="code-block max-h-[65vh]" tabIndex={0}>
            {formatContent(content, path)}
          </pre>
        )}
      </DialogContent>
    </Dialog>
  );
}
function formatContent(content: string, path: string) {
  if (path.endsWith(".json")) {
    try {
      return JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      /* Preserve malformed source verbatim. */
    }
  }
  return content;
}

/** Keep evidence metadata readable, while turning actual file references into previews. */
export function Evidence({ value }: { value: unknown }) {
  const workspace = useContext(EvidenceWorkspace);
  if (value == null) return <span>未附证据</span>;
  if (Array.isArray(value))
    return (
      <div className="flex flex-col gap-3">
        {value.map((item, i) => (
          <Evidence key={i} value={item} />
        ))}
      </div>
    );
  if (typeof value === "object")
    return (
      <dl className="flex min-w-0 flex-col gap-2">
        {Object.entries(value).map(([key, item]) => (
          <div key={key} className="min-w-0">
            <dt className="text-xs text-muted-foreground">
              {(
                {
                  source: "引用文件",
                  scope: "证据范围",
                  call_ids: "关联调用",
                  case_id: "问题",
                } as Record<string, string>
              )[key] || key}
            </dt>
            <dd className="min-w-0">
              <Evidence value={item} />
            </dd>
          </div>
        ))}
      </dl>
    );
  return (
    <span className="whitespace-pre-wrap break-words text-sm leading-relaxed">
      {referenceParts(String(value), workspace?.root).map((part, i) =>
        part.path ? (
          <FileReference key={i} reference={part.text} />
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </span>
  );
}
