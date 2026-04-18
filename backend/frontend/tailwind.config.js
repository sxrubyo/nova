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
        },
        // AI Provider Colors
        openai: {
          DEFAULT: '#10a37f',
          light: '#1dd8a7',
          dark: '#0d7a5f',
        },
        anthropic: {
          DEFAULT: '#d97757', // Claude orange
          light: '#e8987a',
          dark: '#c95a3a',
        },
        google: {
          DEFAULT: '#4285f4',
          light: '#6a9cf9',
          dark: '#3367d6',
        },
        meta: {
          DEFAULT: '#0668e1',
          light: '#3b82f6',
          dark: '#0347a8',
        },
        groq: {
          DEFAULT: '#f55036',
          light: '#ff6b4a',
          dark: '#d63031',
        },
        xai: {
          DEFAULT: '#000000',
          light: '#333333',
          dark: '#1a1a1a',
        },
      },
      boxShadow: {
        'glow': '0 0 20px rgba(62, 207, 142, 0.3)',
        'glow-lg': '0 0 40px rgba(62, 207, 142, 0.4)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.06)',
        'card-dark': '0 4px 24px rgba(0, 0, 0, 0.4)',
      },
      letterSpacing: {
        tightest: '-.075em',
        tighter: '-.05em',
      }
    },
  },
  plugins: [],
}
