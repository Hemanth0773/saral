/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          yellow: '#F9C915',
          darkYellow: '#E5B80B',
          paleYellow: '#FDE047',
          cream: '#FEF9C3',
          black: '#0D0D0D',
          charcoal: '#171717',
          grayBadge: '#F4F4F5'
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'sans-serif'],
        mono: ['"Space Grotesk"', 'monospace'],
      },
      boxShadow: {
        'neubrutal': '4px 4px 0px 0px #0D0D0D',
        'neubrutal-sm': '2px 2px 0px 0px #0D0D0D',
        'neubrutal-hover': '6px 6px 0px 0px #0D0D0D',
        'neubrutal-lg': '6px 6px 0px 0px #0D0D0D',
        'neubrutal-lg-hover': '8px 8px 0px 0px #0D0D0D',
      }
    }
  },
  plugins: [],
}