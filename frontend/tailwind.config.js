/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#007AFF',
          600: '#007AFF',
          700: '#0056CC',
        },
        gray: {
          50: '#F2F2F7',
          100: '#F2F2F7',
          200: '#E5E5EA',
          300: '#D1D1D6',
          400: '#C7C7CC',
          500: '#AEAEB2',
          600: '#8E8E93',
          700: '#3A3A3C',
          800: '#2C2C2E',
          900: '#1C1C1E',
        },
        success: {
          500: '#34C759',
          600: '#34C759',
        },
        warning: {
          500: '#FF9500',
          600: '#FF9500',
        },
        danger: {
          500: '#FF3B30',
          600: '#FF3B30',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
      },
      boxShadow: {
        'apple': '0 4px 16px rgba(0, 0, 0, 0.1)',
      },
    },
  },
  plugins: [],
}
