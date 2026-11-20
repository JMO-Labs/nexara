/**
 * @file theme/palette.ts
 * @brief Glass bento color tokens (solid hex tokens only) (mirrors CSS vars in app/globals.css).
 */

export type TokenName =
  | "bg"
  | "surface"
  | "surface-strong"
  | "ink"
  | "accent"
  | "sun"
  | "leaf"
  | "muted"
  | "nav-muted"
  | "danger"
  | "danger-fg"
  | "blue"
  | "red"
  | "ok"
  | "glass-solid";

export const palette: {
  light: Record<TokenName, string>;
  dark: Record<TokenName, string>;
} = {
  light: {
    bg: "#E4E4E4",
    surface: "#F5F6F9",
    "surface-strong": "#10141A",
    ink: "#10141A",
    accent: "#3B5E9E",
    sun: "#E9C27A",
    leaf: "#45A29C",
    muted: "#4C5361",
    "nav-muted": "#4C5361",
    danger: "#A94242",
    "danger-fg": "#FFFFFF",
    blue: "#83A2DB",
    red: "#CE6969",
    ok: "#3E9E68",
    "glass-solid": "#F1F3F6",
  },
  dark: {
    bg: "#0D1117",
    surface: "#1A202A",
    "surface-strong": "#E9ECF2",
    ink: "#E9ECF2",
    accent: "#A9C1EE",
    sun: "#E4BC72",
    leaf: "#5BB8B1",
    muted: "#A9B0BD",
    "nav-muted": "#A9B0BD",
    danger: "#DB7B7B",
    "danger-fg": "#10141A",
    blue: "#8FAEE6",
    red: "#DB7B7B",
    ok: "#5CC08A",
    "glass-solid": "#1A202A",
  },
};
