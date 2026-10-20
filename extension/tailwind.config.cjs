/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./popup.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        saral: {
          yellow: '#F9C915',
          darkYellow: '#E5B80B',
          paleYellow: '#FEF08A',
          ink: '#0D0D0D',
          charcoal: '#171717',
          surface: '#FBF8FC',
          lavender: '#F4F2F9',
          lavenderHigh: '#E7E4EF',
          lavenderHighest: '#DEDBE9',
          outline: '#C9C4D6',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        brutal: '4px 4px 0px 0px #0D0D0D',
        'brutal-sm': '2px 2px 0px 0px #0D0D0D',
        'brutal-lg': '6px 6px 0px 0px #0D0D0D',
        'brutal-yellow': '3px 3px 0px 0px #735C00',
      },
      maxWidth: {
        popup: '400px',
      },
    },
  },
  plugins: [],
}
