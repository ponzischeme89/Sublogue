import tailwindcssAnimate from 'tailwindcss-animate'

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{svelte,js,ts}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica', 'Arial', 'sans-serif'],
      },
      colors: {
        'bg-primary': 'var(--bg-primary, #000000)',
        'bg-secondary': 'var(--bg-secondary, #0a0a0a)',
        'bg-card': 'var(--bg-card, #0f0f0f)',
        'bg-hover': 'var(--bg-hover, #1a1a1a)',
        'text-primary': 'var(--text-primary, #ffffff)',
        'text-secondary': 'var(--text-secondary, #888888)',
        'text-tertiary': 'var(--text-tertiary, #555555)',
        border: 'var(--border, #1a1a1a)',
        input: 'var(--input, #1a1a1a)',
        ring: 'var(--ring, rgba(15, 23, 42, 0.2))',
        background: 'var(--background, #ffffff)',
        foreground: 'var(--foreground, #0f172a)',
        primary: {
          DEFAULT: 'var(--primary, #0f172a)',
          foreground: 'var(--primary-foreground, #f8fafc)',
        },
        secondary: {
          DEFAULT: 'var(--secondary, #f1f5f9)',
          foreground: 'var(--secondary-foreground, #0f172a)',
        },
        destructive: {
          DEFAULT: 'var(--destructive, #ef4444)',
          foreground: 'var(--destructive-foreground, #fef2f2)',
        },
        muted: {
          DEFAULT: 'var(--muted, #f1f5f9)',
          foreground: 'var(--muted-foreground, #64748b)',
        },
        accent: {
          DEFAULT: 'var(--accent, #3b82f6)',
          foreground: 'var(--accent-foreground, #f8fafc)',
        },
        popover: {
          DEFAULT: 'var(--popover, #ffffff)',
          foreground: 'var(--popover-foreground, #0f172a)',
        },
        card: {
          DEFAULT: 'var(--card, #ffffff)',
          foreground: 'var(--card-foreground, #0f172a)',
        },
      },
      borderRadius: {
        lg: 'var(--radius, 0.5rem)',
        md: 'calc(var(--radius, 0.5rem) - 2px)',
        sm: 'calc(var(--radius, 0.5rem) - 4px)',
      },
    },
  },
  plugins: [tailwindcssAnimate],
}
