/**
 * Theme definitions for Agent-B-Research workbench.
 * Each theme provides CSS custom properties applied to :root.
 */

export const THEME_NAMES = [
  "light",
  "dark",
  "monokai",
  "dracula",
  "nord",
  "solarized-dark",
  "one-dark",
  "catppuccin",
] as const;

export type ThemeName = (typeof THEME_NAMES)[number];

export function isValidTheme(value: unknown): value is ThemeName {
  return typeof value === "string" && THEME_NAMES.includes(value as ThemeName);
}

export interface ThemeColors {
  /** Main background */
  bg: string;
  /** Secondary / sidebar background */
  bgSecondary: string;
  /** Primary text */
  text: string;
  /** Muted / secondary text */
  textMuted: string;
  /** Accent / link color */
  accent: string;
  /** Border color */
  border: string;
  /** Whether Tailwind `dark` class should be applied */
  isDark: boolean;
  /** Display label */
  label: string;
  /** Preview swatch colors (for the theme picker card) */
  swatches: string[];
}

export const themes: Record<ThemeName, ThemeColors> = {
  light: {
    bg: "#ffffff",
    bgSecondary: "#f8fafc",
    text: "#0f172a",
    textMuted: "#64748b",
    accent: "#3b82f6",
    border: "#e2e8f0",
    isDark: false,
    label: "Light",
    swatches: ["#ffffff", "#f8fafc", "#3b82f6", "#0f172a"],
  },
  dark: {
    bg: "#0f172a",
    bgSecondary: "#1e293b",
    text: "#f1f5f9",
    textMuted: "#94a3b8",
    accent: "#3b82f6",
    border: "#334155",
    isDark: true,
    label: "Dark",
    swatches: ["#0f172a", "#1e293b", "#3b82f6", "#f1f5f9"],
  },
  monokai: {
    bg: "#272822",
    bgSecondary: "#1e1f1c",
    text: "#f8f8f2",
    textMuted: "#75715e",
    accent: "#a6e22e",
    border: "#3e3d32",
    isDark: true,
    label: "Monokai",
    swatches: ["#272822", "#a6e22e", "#f92672", "#e6db74"],
  },
  dracula: {
    bg: "#282a36",
    bgSecondary: "#21222c",
    text: "#f8f8f2",
    textMuted: "#6272a4",
    accent: "#bd93f9",
    border: "#44475a",
    isDark: true,
    label: "Dracula",
    swatches: ["#282a36", "#bd93f9", "#ff79c6", "#8be9fd"],
  },
  nord: {
    bg: "#2e3440",
    bgSecondary: "#3b4252",
    text: "#eceff4",
    textMuted: "#d8dee9",
    accent: "#88c0d0",
    border: "#4c566a",
    isDark: true,
    label: "Nord",
    swatches: ["#2e3440", "#88c0d0", "#81a1c1", "#a3be8c"],
  },
  "solarized-dark": {
    bg: "#002b36",
    bgSecondary: "#073642",
    text: "#839496",
    textMuted: "#586e75",
    accent: "#2aa198",
    border: "#073642",
    isDark: true,
    label: "Solarized Dark",
    swatches: ["#002b36", "#2aa198", "#268bd2", "#b58900"],
  },
  "one-dark": {
    bg: "#282c34",
    bgSecondary: "#21252b",
    text: "#abb2bf",
    textMuted: "#5c6370",
    accent: "#61afef",
    border: "#3e4452",
    isDark: true,
    label: "One Dark",
    swatches: ["#282c34", "#61afef", "#e06c75", "#98c379"],
  },
  catppuccin: {
    bg: "#1e1e2e",
    bgSecondary: "#181825",
    text: "#cdd6f4",
    textMuted: "#a6adc8",
    accent: "#89b4fa",
    border: "#313244",
    isDark: true,
    label: "Catppuccin",
    swatches: ["#1e1e2e", "#89b4fa", "#f5c2e7", "#a6e3a1"],
  },
};
