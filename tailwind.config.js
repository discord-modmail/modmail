module.exports = {
  darkMode: 'class', // or 'media' or 'class'
  theme: {
    extend: {},
  },
  variants: {
    extend: {},
  },
  purge: {
    content: ['./templates/**/*.html',],
    options: {
      keyframes: true,
    },
  },
  plugins: [],
}
