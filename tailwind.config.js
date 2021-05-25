module.exports = {
  darkMode: 'class', // or 'media' or 'class'
  theme: {
    extend: {},
  },
  variants: {
    extend: {},
  },
  purge: {
    enabled: true,
    content: ['./src/**/*.html'],
    options: {
      keyframes: true,
    },
  },
  plugins: [],
}
