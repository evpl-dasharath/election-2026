/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Alliance colors
        udf: '#1A8FE3',
        ldf: '#D42B2B',
        nda: '#F7921C',
        oth: '#6B7280',
        
        // Brand/Theme colors
        pagebg: '#F5F2EE',
        surface: '#FDFCFB',
        ink: '#1A1611',
        ink2: '#5C5245',
        pageborder: '#E2DDD8',
        gold: '#C8A84B',
        'live-pulse': '#22c55e',
      },
      fontFamily: {
        sans: ['DM Sans', 'sans-serif'],
        serif: ['DM Serif Display', 'serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      gridTemplateColumns: {
        'dual': '340px 1fr',
      }
    },
  },
  plugins: [],
}

