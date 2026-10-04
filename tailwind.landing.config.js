/** Tailwind config for the standalone landing page: app tokens plus a small `xs` breakpoint. */
const app = require('./tailwind.app.config.js');
const { screens } = require('tailwindcss/defaultTheme');

module.exports = {
  presets: [app],
  content: ['./dashboard/templates/dashboard/landing.html'],
  theme: {
    // Not `extend`: a breakpoint smaller than `sm` must come first or it sorts last.
    screens: { xs: '420px', ...screens },
  },
};