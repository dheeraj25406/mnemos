/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        mnemos: {
          bg: "#090A0B",        // Pitch deep black
          surface: "#111315",   // Charcoal surface
          card: "#16181B",      // Elevated component card
          border: "#23262B",    // Subtle silver-grey border
          accent: "#D1D5DB",    // Subtle silver accent
          muted: "#6B7280",     // Muted steel text
          text: "#F3F4F6",      // Primary crisp text
          highlight: "#E5E7EB", // High contrast white-silver
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "SF Mono", "Fira Code", "monospace"],
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
      },
    },
  },
  plugins: [],
};
