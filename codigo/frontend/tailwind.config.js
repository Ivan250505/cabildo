/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary:  { DEFAULT: "#B22222", hover: "#8B1A1A" },
        navy:     { DEFAULT: "#1A3A5C", light: "#2A5080" },
        gold:     { DEFAULT: "#C8922A", light: "#E6A830" },
        success:  "#2E7D32",
        warning:  "#FF9800",
        danger:   "#F44336",
      },
      fontFamily: {
        heading: ["'Playfair Display'", "Georgia", "serif"],
        body:    ["'Source Sans 3'", "'Source Sans Pro'", "sans-serif"],
      },
    },
  },
  plugins: [],
}
