/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        mono: ['IBM Plex Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
        sans: ['Manrope', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: {
          DEFAULT: '#000000',
          foreground: '#FFFFFF',
        },
        accent: {
          DEFAULT: '#3ecf8e', // Nova Green
          foreground: '#FFFFFF',
        },
        background: {
          light: '#FFFFFF',
          dark: '#050505', // Much softer than pure black
        },
        surface: {
          light: '#F9F9F9',
          dark: '#0D0D0D', // Soft charcoal
        },
        card: {
          light: '#FFFFFF',
          dark: '#121212', // Slightly lighter for contrast
        },
        border: {
          light: '#E5E5E5',
          dark: '#1A1A1A',
        },
        muted: {
          light: '#737373',
          dark: '#A3A3A3',
        }
      },
      letterSpacing: {
        tightest: '-.075em',
        tighter: '-.05em',
      }
    },
  },
  plugins: [],
}
