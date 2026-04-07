/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ufc: {
          gold: '#C9A227',
          'gold-muted': '#9A7B1A',
          red: '#B91C1C',
          'red-light': '#DC2626',
          dark: '#0A0A0A',
          surface: '#111111',
          card: '#161616',
          'card-hover': '#1A1A1A',
          border: '#222222',
          'border-light': '#2A2A2A',
          text: '#E8E8E8',
          muted: '#737373',
          'muted2': '#525252',
          blue: '#3B82B0',
        },
      },
      fontFamily: {
        sans: ['"Helvetica Neue"', 'Helvetica', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
}