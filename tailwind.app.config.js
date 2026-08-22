/** Tailwind config for the authenticated app shell (base.html and everything that extends it). */
module.exports = {
  content: [
    './templates/**/*.html',
    './dashboard/templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        // Brand & Accent (from DESIGN.md)
        "primary": "#9FE870",
        "primary-active": "#CDFFAD",
        "primary-hover": "#CDFFAD",
        "primary-neutral": "#C5EDAB",
        "primary-pale": "#E2F6D5",
        "on-primary": "#0E0F0C",

        // Canvas & Surface
        "canvas": "#FFFFFF",
        "canvas-soft": "#E8EBE6",
        "background": "#E8EBE6",
        "surface": "#FFFFFF",
        "surface-container-lowest": "#FFFFFF",
        "surface-container-low": "#F0F3EE",
        "surface-container": "#E8EBE6",
        "surface-container-high": "#DFE3DD",
        "surface-container-highest": "#D5D9D3",
        "soft-green": "#E2F6D5",
        "warm-cream": "#E8EBE6",

        // Text & Ink
        "ink": "#0E0F0C",
        "ink-deep": "#163300",
        "deep-forest": "#163300",
        "on-surface": "#0E0F0C",
        "on-surface-variant": "#454745",
        "body": "#454745",
        "mute": "#868685",
        "neutral": "#868685",

        // Borders & Outlines
        "outline": "#868685",
        "outline-variant": "#D5D9D3",
        "light-border": "#D5D9D3",

        // Semantic
        "positive": "#2EAD4B",
        "positive-deep": "#054D28",
        "income": "#2EAD4B",
        "safe": "#2EAD4B",
        "warning": "#FFD11A",
        "warning-deep": "#B86700",
        "warning-content": "#4A3B1C",
        "negative": "#D03238",
        "negative-deep": "#A72027",
        "negative-darkest": "#A7000D",
        "negative-bg": "#320707",
        "expense": "#D03238",
        "error": "#D03238",

        // Tertiary Brand Accents
        "accent-orange": "#FFC091",
        "accent-cyan": "#38C8FF",
      },
      borderRadius: {
        "sm": "8px",
        "md": "12px",
        "lg": "16px",
        "xl": "24px",
        "2xl": "24px",
        "3xl": "32px",
        "pill": "9999px",
        "full": "9999px",
      },
      spacing: {
        "xxs": "2px",
        "xs": "4px",
        "sm": "8px",
        "md": "12px",
        "lg": "16px",
        "xl": "24px",
        "2xl": "32px",
        "3xl": "48px",
        "touch-target-min": "48px",
        "gutter": "16px",
        "margin-mobile": "16px",
      },
      fontFamily: {
        "sans": ["Inter", "sans-serif"],
        "display": ["Inter", "sans-serif"],
      },
      fontSize: {
        "display-mega": ["126px", { "lineHeight": "107px", "fontWeight": "900" }],
        "display-xxl": ["96px", { "lineHeight": "82px", "fontWeight": "900" }],
        "display-xl": ["64px", { "lineHeight": "54px", "fontWeight": "900" }],
        "display-lg": ["47px", { "lineHeight": "70px", "fontWeight": "400" }],
        "display-md": ["40px", { "lineHeight": "34px", "fontWeight": "900" }],
        "display-sm": ["32px", { "lineHeight": "38px", "fontWeight": "600" }],
        "display-xs": ["24px", { "lineHeight": "31px", "fontWeight": "600" }],
        "body-lg": ["20px", { "lineHeight": "30px", "fontWeight": "400" }],
        "body-md": ["16px", { "lineHeight": "24px", "fontWeight": "400" }],
        "body-md-strong": ["16px", { "lineHeight": "24px", "fontWeight": "600" }],
        "body-sm": ["14px", { "lineHeight": "20px", "fontWeight": "400" }],
        "body-sm-strong": ["14px", { "lineHeight": "20px", "fontWeight": "600" }],
        "caption": ["12px", { "lineHeight": "16px", "fontWeight": "400" }],
        "button-md": ["16px", { "lineHeight": "24px", "fontWeight": "600" }],
      },
      boxShadow: {
        "soft": "0 2px 12px rgba(14, 15, 12, 0.04)",
        "elevated": "0 8px 24px rgba(14, 15, 12, 0.08)",
        "xs": "0 1px 3px rgba(14, 15, 12, 0.04)",
      },
    },
  },
  future: {
    hoverOnlyWhenSupported: true,
  },
};
