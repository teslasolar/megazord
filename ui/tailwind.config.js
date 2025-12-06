/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ISA-101 Color Scheme
        dark: '#0A0A0F',
        surface: '#1A1A2E',
        'surface-light': '#2A2A3E',
        accent: '#06B6D4',
        success: '#22C55E',
        warning: '#F59E0B',
        error: '#EF4444',
        info: '#06B6D4',
      },
    },
  },
  plugins: [],
}
