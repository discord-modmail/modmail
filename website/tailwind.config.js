module.exports = {
  darkMode: 'class', // or 'media' or 'class'
  theme: {
    extend: {},
  },
  variants: {
    extend: {},
  },
  purge: {
    content: ['./website/templates/**/*.html',],
    options: {
      keyframes: true,
    },
  },
  plugins: [],
}
