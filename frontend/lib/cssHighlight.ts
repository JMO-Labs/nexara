/**
 * @file lib/cssHighlight.ts
 * @brief Tiny dependency-free CSS tokenizer for editor syntax highlighting.
 */

export type CssTokenType =
  | "comment"
  | "string"
  | "atrule"
  | "brace"
  | "punct"
  | "selector"
  | "property"
  | "value"
  | "text";

export interface CssToken {
  type: CssTokenType;
  text: string;
}

/** @brief Max stored custom CSS size in bytes (mirrors backend MAX_CSS_BYTES). */
export const MAX_CSS_BYTES = 10240;

const TOKEN_RE =
  /(\/\*[\s\S]*?(?:\*\/|$))|("(?:[^"\\\n]|\\.)*"?|'(?:[^'\\\n]|\\.)*'?)|(@[\w-]+)|([{}])|([:;,()])|([^\s{}:;,()"'/]+|\/)|(\s+)/g;

/**
 * @brief Split CSS into typed tokens; concatenated texts equal the input.
 * @param src CSS source
 * @return tokens in source order
 */
export function tokenizeCss(src: string): CssToken[] {
  const out: CssToken[] = [];
  let depth = 0;
  let inValue = false;
  for (const m of src.matchAll(TOKEN_RE)) {
    const [text, comment, str, at, brace, punct, word] = m;
    let type: CssTokenType = "text";
    if (comment) type = "comment";
    else if (str) type = "string";
    else if (at) type = "atrule";
    else if (brace) {
      type = "brace";
      depth = Math.max(0, depth + (brace === "{" ? 1 : -1));
      inValue = false;
    } else if (punct) {
      type = "punct";
      if (punct === ";") inValue = false;
      else if (punct === ":" && depth > 0 && isDeclColon(src, m.index ?? 0))
        inValue = true;
    } else if (word) {
      if (inValue) type = "value";
      else if (
        depth > 0 &&
        isDeclColon(src, after(src, (m.index ?? 0) + text.length))
      )
        type = "property";
      else type = "selector";
    }
    out.push({ type, text });
  }
  return out;
}

function after(src: string, i: number): number {
  while (i < src.length && /\s/.test(src[i])) i++;
  return i;
}

/** A colon starts a declaration if a `;`/`}`/EOF comes before any `{`. */
function isDeclColon(src: string, i: number): boolean {
  if (src[i] !== ":") return false;
  const rest = src.slice(i + 1);
  const brace = rest.search(/[{]/);
  const end = rest.search(/[;}]/);
  return brace === -1 || (end !== -1 && end < brace);
}

/**
 * @brief UTF-8 byte length of a string.
 * @param s text
 * @return number of bytes
 */
export const cssByteLength = (s: string): number =>
  new TextEncoder().encode(s).length;
