/** Tailwind config for the standalone marketing landing page (landing.html). */
module.exports = {
  content: ['./dashboard/templates/dashboard/landing.html'],
  theme: {
    screens: {
      'xs': '420px',
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
    },
    extend: {
      fontFamily: {
        sans: ['"Inter"', 'sans-serif'],
        display: ['"Inter"', 'sans-serif'],
      },
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
        "surface-lowest": "#FFFFFF",
        "surface-low": "#F0F3EE",
        "soft-green": "#E2F6D5",
        "warm-cream": "#E8EBE6",

        // Text & Ink
        "ink": "#0E0F0C",
        "ink-deep": "#163300",
        "deep-forest": "#163300",
        "body": "#454745",
        "mute": "#868685",
        "on-surface-variant": "#454745",
        "outline-variant": "#D5D9D3",
        "light-border": "#D5D9D3",

        // Semantic
        "positive": "#2EAD4B",
        "positive-deep": "#054D28",
        "income": "#2EAD4B",
        "warning": "#FFD11A",
        "warning-deep": "#B86700",
        "negative": "#D03238",
        "expense": "#D03238",

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
      boxShadow: {
        "soft": "0 4px 20px rgba(14, 15, 12, 0.05)",
        "elevated": "0 10px 30px rgba(14, 15, 12, 0.10)",
        "xs": "0 1px 3px rgba(14, 15, 12, 0.04)",
      },
    },
  },
};
