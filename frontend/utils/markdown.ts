/**
 * @file utils/markdown.ts
 * @brief Safe Markdown rendering utility.
 *
 * Renders Markdown to HTML using markdown-it and sanitizes the output
 * with DOMPurify to prevent XSS attacks. This is the only sanctioned
 * way to render user-authored Markdown content.
 */

import MarkdownIt from "markdown-it";
import DOMPurify from "dompurify";

/** @brief Configured markdown-it instance with sensible defaults. */
const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
});

/**
 * @brief Render Markdown to sanitized HTML.
 * @param source - Raw Markdown string.
 * @returns Sanitized HTML string safe for innerHTML.
 */
export function renderMarkdown(source: string): string {
  if (!source) return "";
  const raw = md.render(source);
  return DOMPurify.sanitize(raw);
}
