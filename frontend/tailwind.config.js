/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#84cc16', // lime-500
          bright: '#a3e635',  // lime-400
        },
        bg: '#050a05',
        surface: {
          1: '#0d1a0d',
          2: '#132013',
        },
        border: 'rgba(132, 204, 22, 0.15)',
        text: {
          DEFAULT: '#f0fdf0',
          muted: '#6b7280',
        },
        accent: '#ffffff',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['"Space Grotesk"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
