/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{astro,html,js,jsx,ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        sand: {
          50: "#fbf7f2",
          100: "#f6f1ea",
          200: "#e8dfd2",
          300: "#d8cab7",
          400: "#bca890",
        },
        canvas: "#f6f1ea",
        shell: "#fcf8f3",
        graphite: "#221d19",
        accent: "#9f3347",
        blush: {
          50: "#fbefef",
          100: "#f5e4e6",
          200: "#e5c8ce",
          400: "#c6828d",
          500: "#b05a68",
          700: "#7f3d49",
        },
        sage: {
          50: "#f1f4ee",
          100: "#e6ece0",
          200: "#ced8c1",
          400: "#95a680",
          500: "#70825f",
          700: "#526047",
        },
        sky: {
          50: "#eff5f7",
          100: "#e2edf1",
          200: "#c8d8e0",
          400: "#7f9aa9",
          500: "#607c8a",
          700: "#465d69",
        },
        sun: {
          50: "#faf3e5",
          100: "#f6ecd4",
          200: "#ead6aa",
          400: "#d2ae67",
          500: "#b08b40",
          700: "#7d6329",
        },
      },
      fontFamily: {
        sans: ["Geist", "system-ui", "sans-serif"],
        mono: ["Geist Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        "diffuse": "0 18px 38px -28px rgba(34,29,25,0.32)",
      },
    },
  },
  plugins: [],
};
