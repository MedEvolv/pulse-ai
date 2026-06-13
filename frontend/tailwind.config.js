/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        canvas: "#F7F8FA",
        surface: "#FFFFFF",
        ink: "#17212B",
        muted: "#667085",
        line: "#D8DEE8",
        healthy: "#17845B",
        watch: "#C47A00",
        breach: "#C83B3B",
        info: "#1769AA",
        accent: "#00A6A6",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
      borderRadius: { card: "8px" },
      boxShadow: {
        tile: "0 1px 2px rgba(23,33,43,0.06), 0 1px 1px rgba(23,33,43,0.04)",
        drawer: "-8px 0 24px rgba(23,33,43,0.12)",
      },
    },
  },
  plugins: [],
};
