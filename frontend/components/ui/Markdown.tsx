"use client";
/**
 * @file components/ui/Markdown.tsx
 * @brief Safe GFM markdown renderer. Sanitized via rehype-sanitize.
 *        Headings flatten to body weight to fit chat/post density.
 */
import * as React from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";

export interface MarkdownProps {
  content: string;
  truncate?: boolean;
  /** Lines to clamp when truncate is set. Default 6. */
  clampLines?: number;
  /** Override font size. Default inherits parent. */
  size?: "sm" | "md";
}

const schema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    a: [...(defaultSchema.attributes?.a || []), ["target"], ["rel"]],
    code: [...(defaultSchema.attributes?.code || []), ["className"]],
  },
  clobberPrefix: "nx-md-",
};

const components: Components = {
  a: ({ children, href, ...rest }) => (
    <a {...rest} href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  // Flatten headings — chat/posts already have their own heading hierarchy.
  h1: ({ children }) => <strong>{children}</strong>,
  h2: ({ children }) => <strong>{children}</strong>,
  h3: ({ children }) => <strong>{children}</strong>,
  h4: ({ children }) => <strong>{children}</strong>,
  h5: ({ children }) => <strong>{children}</strong>,
  h6: ({ children }) => <strong>{children}</strong>,
};

export function Markdown({
  content,
  truncate,
  clampLines = 6,
  size = "md",
}: MarkdownProps) {
  if (!content?.trim()) return null;
  return (
    <div
      className={cn(
        "nx-md leading-[1.55] text-ink break-words",
        size === "sm" ? "text-sm" : "text-[length:inherit]",
        "[&_p+p]:mt-3 [&_a]:underline [&_a]:text-ink",
        "[&_code]:rounded [&_code]:bg-bg [&_code]:px-1 [&_code]:font-mono [&_code]:text-[0.9em]",
        "[&_pre]:mt-3 [&_pre]:overflow-auto [&_pre]:rounded-lg [&_pre]:bg-bg [&_pre]:p-3 [&_pre_code]:bg-transparent [&_pre_code]:p-0",
        "[&_blockquote]:mt-3 [&_blockquote]:border-l-4 [&_blockquote]:border-leaf [&_blockquote]:pl-3 [&_blockquote]:opacity-80",
        "[&_ul]:mt-2 [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:mt-2 [&_ol]:list-decimal [&_ol]:pl-6",
        "[&_table]:mt-3 [&_table]:border-collapse [&_th]:border [&_td]:border [&_th]:border-ink/20 [&_td]:border-ink/20 [&_th]:px-2 [&_td]:px-2 [&_th]:bg-bg",
        "[&_hr]:my-3 [&_hr]:border-ink/20 [&_img]:max-w-full [&_img]:rounded-lg",
        truncate &&
          "overflow-hidden [display:-webkit-box] [-webkit-box-orient:vertical]",
      )}
      style={truncate ? { WebkitLineClamp: clampLines } : undefined}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, schema]]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default Markdown;
