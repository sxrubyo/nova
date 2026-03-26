/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'IBM Plex Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
        sans: ['Plus Jakarta Sans', 'Inter', 'Manrope', 'system-ui', 'sans-serif'],
        display: ['Plus Jakarta Sans', 'Inter', 'Manrope', 'system-ui', 'sans-serif'],
      },
      colors: {
        nova: {
          void: 'var(--nova-void)',
          surface: 'var(--nova-surface)',
          'surface-2': 'var(--nova-surface-2)',
          border: 'var(--nova-border)',
          'border-active': 'var(--nova-border-active)',
          text: {
            primary: 'var(--nova-text-primary)',
            secondary: 'var(--nova-text-secondary)',
            muted: 'var(--nova-text-muted)',
          },
          accent: 'var(--nova-accent)',
          'accent-glow': 'var(--nova-accent-glow)',
          'accent-2': 'var(--nova-accent-2)',
          success: 'var(--nova-success)',
          warning: 'var(--nova-warning)',
          danger: 'var(--nova-danger)',
          info: 'var(--nova-info)',
        },
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(108, 92, 231, 0.28), 0 18px 40px -20px rgba(108, 92, 231, 0.55)',
        'glow-lg': '0 0 0 1px rgba(108, 92, 231, 0.35), 0 35px 90px -32px rgba(108, 92, 231, 0.62)',
        panel: '0 24px 80px -40px rgba(0, 0, 0, 0.65)',
        float: '0 28px 120px -56px rgba(0, 0, 0, 0.7)',
      },
      letterSpacing: {
        tightest: '-0.075em',
        tighter: '-0.05em',
      },
      backgroundImage: {
        'nova-grid': 'linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)',
        'nova-blueprint': 'radial-gradient(circle at top, rgba(108, 92, 231, 0.18), transparent 32%), linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0))',
      },
      animation: {
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'grid-drift': 'grid-drift 18s linear infinite',
        'spin-slow': 'spin 10s linear infinite',
        shimmer: 'shimmer 1.8s linear infinite',
      },
      keyframes: {
        'grid-drift': {
          '0%': { transform: 'translate3d(0, 0, 0)' },
          '50%': { transform: 'translate3d(0, -12px, 0)' },
          '100%': { transform: 'translate3d(0, 0, 0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
}
