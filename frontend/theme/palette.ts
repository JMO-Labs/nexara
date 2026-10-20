/**
 * @file theme/palette.ts
 * @brief Garden Club color tokens (mirrors CSS vars in app/globals.css).
 */

export type TokenName =
  | "bg"
  | "surface"
  | "surface-strong"
  | "ink"
  | "accent"
  | "sun"
  | "leaf"
  | "muted";

export const palette: {
  light: Record<TokenName, string>;
  dark: Record<TokenName, string>;
} = {
  light: {
    bg: "#E9F1E4",
    surface: "#FFFFFF",
    "surface-strong": "#14301E",
    ink: "#14301E",
    accent: "#C6B4F5",
    sun: "#F2D16B",
    leaf: "#7BAE7F",
    muted: "#9DB8A2",
  },
  dark: {
    bg: "#0E1F15",
    surface: "#16291D",
    "surface-strong": "#1B3524",
    ink: "#DCE9D8",
    accent: "#C6B4F5",
    sun: "#C9A94A",
    leaf: "#4E7F56",
    muted: "#86A38C",
  },
};
