/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        display: ["'Space Grotesk'", "'IBM Plex Sans'", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      colors: {
        ink: { 950: "#0a0d12", 900: "#0f141b", 850: "#131a23", 800: "#18202b", 700: "#232d3a", 600: "#334155", 400: "#8a97a8", 300: "#b6c0cc", 100: "#e8edf3" },
        accent: { DEFAULT: "#3ee6a8", dim: "#1f8f68" },
      },
    },
  },
  plugins: [],
};
