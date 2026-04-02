/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{astro,html,js,jsx,ts,tsx}",
    "../templates/**/*.html"
  ],
  theme: {
    extend: {
      colors: {
        sand: {
          50: "#fdf9f5",
          100: "#f9f5f0",
          200: "#e7dfd6",
          300: "#d6c8bc",
        },
        graphite: "#231f1a",
        accent: "#b41632",
      },
      fontFamily: {
        sans: ["Geist", "system-ui", "sans-serif"],
        mono: ["Geist Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        "diffuse": "0 20px 40px -15px rgba(0,0,0,0.08)",
      },
    },
  },
  plugins: [],
};
