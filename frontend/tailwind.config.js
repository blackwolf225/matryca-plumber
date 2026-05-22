/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        cyber: {
          void: '#050810',
          panel: '#0c1220',
          border: '#1e293b',
          emerald: '#34d399',
          amber: '#fbbf24',
          cyan: '#22d3ee',
        },
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'token-flash': 'token-flash 0.55s ease-out',
        'status-pulse': 'status-pulse 1.8s ease-in-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 8px rgb(52 211 153 / 0.35)' },
          '50%': { boxShadow: '0 0 22px rgb(52 211 153 / 0.75)' },
        },
        'token-flash': {
          '0%': { color: '#6ee7b7', textShadow: '0 0 12px rgb(52 211 153 / 0.9)' },
          '100%': { color: '#34d399', textShadow: '0 0 4px rgb(52 211 153 / 0.4)' },
        },
        'status-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.65' },
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
}
