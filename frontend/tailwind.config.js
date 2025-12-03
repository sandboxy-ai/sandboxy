/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Orange accent colors (matching the MVP)
        accent: {
          DEFAULT: '#f97316',
          hover: '#fb923c',
          dark: '#ea580c',
        },
        // Dark theme
        dark: {
          bg: '#0a0a0b',
          card: '#141415',
          border: '#2a2a2c',
          hover: '#1c1c1e',
        },
      },
    },
  },
  plugins: [],
}
