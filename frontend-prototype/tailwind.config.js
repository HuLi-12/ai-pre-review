/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cockpit: {
          bg: '#0B1020',
          card: '#131A2E',
          border: '#1E2A45',
          primary: '#38BDF8',
          text: '#E2E8F0',
          muted: '#64748B',
          critical: '#EF4444',
          high: '#F59E0B',
          medium: '#3B82F6',
          low: '#6B7280',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}

