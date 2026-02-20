import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        sinal: {
          black: '#0A0A0B',
          graphite: '#1A1A1F',
          slate: '#2A2A32',
        },
        ash: '#8A8A96',
        silver: '#C4C4CC',
        bone: '#F0EDE8',
        'sinal-white': '#FAFAF8',
        signal: {
          DEFAULT: '#E8FF59',
          dim: '#C4D94B',
        },
        agent: {
          sintese: '#E8FF59',
          radar: '#59FFB4',
          codigo: '#59B4FF',
          funding: '#FF8A59',
          mercado: '#C459FF',
        },
      },
      fontFamily: {
        display: ['var(--font-display)', 'Georgia', 'serif'],
        body: ['var(--font-body)', '-apple-system', 'sans-serif'],
        mono: ['var(--font-mono)', 'Courier New', 'monospace'],
      },
      maxWidth: {
        container: '1080px',
      },
      borderColor: {
        'slate-border': 'rgba(255,255,255,0.06)',
      },
      backgroundColor: {
        'signal-bg': 'rgba(232,255,89,0.06)',
        'signal-bg-hover': 'rgba(232,255,89,0.10)',
      },
      padding: {
        section: 'clamp(80px, 10vw, 140px)',
      },
      animation: {
        'fade-up': 'fadeUp 0.6s ease-out forwards',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(24px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
