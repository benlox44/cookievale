/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        serif: ["Playfair Display", "serif"],
      },
      colors: {
        cookie: {
          pink: "#fdd0cd",
          peach: "#F4A07A",
          golden: "#D4956A",
          brown: "#7B3F2B",
          cream: "#FDF5EE",
        },
      },
    },
  },
  plugins: [],
};
