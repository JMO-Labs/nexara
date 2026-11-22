/**
 * @file theme/palette.ts
 * @brief Glass bento color tokens, Aegean palette ("whitewash & bougainvillea") (solid hex tokens only) (mirrors CSS vars in app/globals.css).
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
    bg: "#F6F1EB",
    surface: "#FBF9F6",
    "surface-strong": "#24323D",
    ink: "#24323D",
    accent: "#2F5873",
    sun: "#C9973F",
    leaf: "#6B7D4A",
    muted: "#55636D",
    "nav-muted": "#55636D",
    danger: "#A94242",
    "danger-fg": "#FFFFFF",
    blue: "#A9BCC4",
    red: "#A8505F",
    ok: "#3E9E68",
    "glass-solid": "#F7F2EC",
  },
  dark: {
    bg: "#111A22",
    surface: "#1C2834",
    "surface-strong": "#F1EBE4",
    ink: "#F1EBE4",
    accent: "#A9C9DB",
    sun: "#E6C07A",
    leaf: "#B4C58E",
    muted: "#A9B5BD",
    "nav-muted": "#A9B5BD",
    danger: "#DB7B7B",
    "danger-fg": "#111A22",
    blue: "#8FB6CF",
    red: "#E7A3AE",
    ok: "#5CC08A",
    "glass-solid": "#1C2834",
  },
};
