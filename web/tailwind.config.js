/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"Instrument Serif"', 'Georgia', 'serif'],
        sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        pixel: ['"Press Start 2P"', 'monospace', 'cursive'],
        handwriting: ['"Caveat"', '"Indie Flower"', 'cursive', 'sans-serif'],
      },
      colors: {
        paper: '#FAF9F6',
        ink: '#111215',
        cardBlue: '#163172',
        cardYellow: '#FFD700',
        cardGreen: '#10B981',
        cardPurple: '#6D28D9',
        cardPink: '#EC4899',
      }
    },
  },
  plugins: [],
}
