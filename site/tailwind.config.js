module.exports = {
  darkMode: 'class', // or 'media' or 'class'
  theme: {
    extend: {},
  },
  variants: {
    extend: {},
  },
  purge: {
    content: ['.site/templates/**/*.html',],
    options: {
      keyframes: true,
    },
  },
  plugins: [],
}
