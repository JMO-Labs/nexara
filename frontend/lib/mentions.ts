/**
 * @file lib/mentions.ts
 * @brief @username helpers: markdown linkify (outside code) and the active
 *        "@query" before the caret for pickers.
 */

const MENTION = /(^|[^\w@/`])@([a-zA-Z0-9_-]{1,64})/g;

/**
 * @brief Turn @username into markdown links to /app/u/username, leaving
 *        inline code and fenced blocks alone.
 * @param md markdown text
 * @return markdown with mention links
 */
export function linkifyMentions(md: string): string {
  return md
    .split(/(```[\s\S]*?```|`[^`\n]*`)/g)
    .map((part, i) =>
      i % 2
        ? part
        : part.replace(
            MENTION,
            (_m, pre: string, name: string) =>
              `${pre}[@${name}](/app/u/${name})`,
          ),
    )
    .join("");
}

/**
 * @brief The "@query" being typed right before the caret, if any.
 * @param text full text
 * @param caret caret index
 * @return { start, query } where start is the index of "@", or null
 */
export function activeMention(
  text: string,
  caret: number,
): { start: number; query: string } | null {
  const m = /(^|\s)@([a-zA-Z0-9_-]{0,64})$/.exec(text.slice(0, caret));
  return m ? { start: caret - m[2].length - 1, query: m[2] } : null;
}
