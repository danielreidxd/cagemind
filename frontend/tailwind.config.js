/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ufc: {
          gold: '#D4AF37',
          red: '#C8102E',
          dark: '#0D0D0D',
          gray: '#1A1A2E',
          blue: '#16213E',
          card: '#1C1C3A',
          border: '#2A2A4A',
          text: '#E0E0E0',
          muted: '#8888AA',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
