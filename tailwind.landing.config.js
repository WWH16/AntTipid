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
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
        display: ['"Outfit"', '"Plus Jakarta Sans"', 'sans-serif'],
      },
      colors: {
        "primary": "#5C8F3A",
        "ant-green": "#5C8F3A",
        "deep-forest": "#23452A",
        "secondary": "#23452A",
        "warm-cream": "#F8F5EA",
        "soft-green": "#E7F1D9",
        "soft-yellow": "#F3D27A",
        "light-border": "#E5E5DD",
        "surface-lowest": "#FFFFFF",
        "surface-low": "#F3EFE4",
        "expense": "#D96B4A",
        "warning": "#E4A72C",
        "on-surface-variant": "#434B41",
        "outline-variant": "#E5E5DD",
      },
      boxShadow: {
        "soft": "0 4px 20px rgba(35, 69, 42, 0.06)",
        "elevated": "0 10px 30px rgba(35, 69, 42, 0.12)",
        "xs": "0 1px 3px rgba(35, 69, 42, 0.05)",
      },
    },
  },
};
