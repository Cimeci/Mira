import type { Config } from "tailwindcss";

/**
 * Mira design tokens (see project/uploads/design.md).
 * Colors, type scale, effects, and clip-path are surfaced here so screens and
 * components reference tokens rather than hardcoded literals.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        mira: {
          void: "#0B0710",
          "void-deep": "#06040A", // page canvas behind the 1440 frame
          night: "#140E1F",
          "purple-steel": "#1E132B",
          "neon-purple": "#6B2FA5",
          "electric-lilac": "#B56BFF",
          "lilac-glow": "#D7B3FF",
          luminance: "#F2E6FF",
          "muted-text": "#9A8AAE",
          "muted-dim": "#6E5F82", // secondary muted used across the prototype
          disabled: "#4B4058",
          "panel-border": "#6F3E91",
          paper: "#F2EDE0", // mandate contract sheet
          "paper-ink": "#241A2E",
          "paper-muted": "#6d5f7a",
        },
      },
      fontFamily: {
        display: ["var(--font-silkscreen)", "monospace"],
        mono: ["var(--font-plex-mono)", "'Courier New'", "monospace"],
      },
      fontSize: {
        wordmark: ["64px", { lineHeight: "1.05" }],
        "display-lg": ["42px", { lineHeight: "1.05" }],
        section: ["20px", { lineHeight: "1.2" }],
        label: ["12px", { lineHeight: "1" }],
        "body-lg": ["16px", { lineHeight: "1.45" }],
        "body-sm": ["13px", { lineHeight: "1.45" }],
        caption: ["11px", { lineHeight: "1.45" }],
        terminal: ["14px", { lineHeight: "1.45" }],
      },
      letterSpacing: {
        display: "0.04em",
        label: "0.08em",
      },
      borderRadius: {
        panel: "10px",
        card: "8px",
        chip: "6px",
        progress: "4px",
      },
      boxShadow: {
        "glow-soft":
          "0 0 8px rgba(181,107,255,0.45), 0 0 18px rgba(107,47,165,0.35)",
        "glow-strong":
          "0 0 6px rgba(242,230,255,0.8), 0 0 14px rgba(181,107,255,0.75), 0 0 28px rgba(107,47,165,0.55)",
        "border-glow":
          "0 0 0 1px rgba(181,107,255,0.9), 0 0 12px rgba(181,107,255,0.55)",
        panel:
          "inset 0 0 0 1px rgba(181,107,255,0.22), 0 0 24px rgba(107,47,165,0.18)",
        card:
          "inset 0 0 0 1px rgba(181,107,255,0.35), 0 0 14px rgba(107,47,165,0.22)",
      },
      textShadow: {
        glow: "0 0 4px rgba(242,230,255,0.9), 0 0 12px rgba(181,107,255,0.75)",
      },
      keyframes: {
        blink: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0" } },
        pulse: {
          "0%,100%": { boxShadow: "0 0 8px rgba(181,107,255,0.45)" },
          "50%": { boxShadow: "0 0 18px rgba(181,107,255,0.8)" },
        },
        flow: {
          "0%": { backgroundPosition: "0% 50%" },
          "100%": { backgroundPosition: "200% 50%" },
        },
        crt: {
          "0%,100%": {
            textShadow:
              "0 0 2px rgba(242,230,255,0.95), 0 0 8px rgba(215,179,255,0.85), 0 0 22px rgba(181,107,255,0.75), 0 0 48px rgba(107,47,165,0.6)",
            opacity: "1",
          },
          "50%": {
            textShadow:
              "0 0 3px rgba(242,230,255,1), 0 0 12px rgba(215,179,255,0.95), 0 0 30px rgba(181,107,255,0.85), 0 0 64px rgba(107,47,165,0.7)",
            opacity: "0.96",
          },
          "92%": { opacity: "0.88" },
        },
        spin: {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        softpulse: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.45" } },
        shine: {
          "0%,100%": {
            filter:
              "drop-shadow(0 0 10px rgba(181,107,255,0.35)) brightness(0.92)",
            opacity: "0.9",
          },
          "50%": {
            filter:
              "drop-shadow(0 0 26px rgba(215,179,255,0.85)) brightness(1.12)",
            opacity: "1",
          },
        },
      },
      animation: {
        blink: "blink 1.2s steps(1) infinite",
        pulse: "pulse 2s ease-in-out infinite",
        flow: "flow 3.2s linear infinite",
        crt: "crt 2.6s ease-in-out infinite",
        spin: "spin 1s linear infinite",
        softpulse: "softpulse 1.6s ease-in-out infinite",
        shine: "shine 3.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
