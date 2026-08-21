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
          pink: "var(--cookie-pink)",
          peach: "var(--cookie-peach)",
          golden: "var(--cookie-golden)",
          brown: "var(--cookie-brown)",
          cream: "var(--cookie-cream)",
        },
      },
    },
  },
  plugins: [],
};
