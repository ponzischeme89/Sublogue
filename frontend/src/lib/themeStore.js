import { writable } from 'svelte/store'

export const themes = {
  oled: {
    name: 'OLED',
    colors: {
      // Backgrounds (true OLED but layered)
      'bg-primary': '#000000',
      'bg-secondary': '#1a1a1a',
      'bg-card': '#0b0b0b',
      'bg-hover': '#2a2a2a',

      // Text
      'text-primary': '#ffffff',
      'text-secondary': '#b0b0b0',
      'text-tertiary': '#7a7a7a',

      // UI chrome
      'border': 'rgba(255, 255, 255, 0.08)',

      // Accents & interaction
      'accent': '#3b82f6',                 // restrained blue
      'button-bg': '#0f0f0f',
      'button-hover': '#1a1a1a',
      'button-text': '#ffffff',
      'focus-ring': 'rgba(255, 255, 255, 0.25)',
    }
  },

  ocean: {
    name: 'Ocean',
    colors: {
      // Backgrounds (deeper, cinematic)
      'bg-primary': '#070f1e',
      'bg-secondary': '#0b162b',
      'bg-card': '#0f1d36',
      'bg-hover': '#162a4a',

      // Text
      'text-primary': '#e6f0ff',
      'text-secondary': '#9bbbe6',
      'text-tertiary': '#6f8fb6',

      // Borders
      'border': 'rgba(120, 170, 220, 0.18)',

      // Accents & interaction (this is the magic)
      'accent': '#5fa8ff',                  // beautiful ocean blue
      'button-bg': '#132646',
      'button-hover': '#1b3560',
      'button-text': '#eaf3ff',
      'focus-ring': 'rgba(95, 168, 255, 0.45)',
    }
  },

  light: {
    name: 'Light',
    colors: {
      'bg-primary': '#f8f9fa',
      'bg-secondary': '#f1f3f5',
      'bg-card': '#ffffff',
      'bg-hover': '#e9ecef',

      'text-primary': '#1a1a1a',
      'text-secondary': '#5c5f66',
      'text-tertiary': '#868e96',

      'border': '#dee2e6',

      'accent': '#2563eb',
      'button-bg': '#ffffff',
      'button-hover': '#f1f3f5',
      'button-text': '#1a1a1a',
      'focus-ring': 'rgba(37, 99, 235, 0.35)',
    }
  }
}

const STORAGE_KEY = 'sublogue-theme'

function getInitialTheme() {
  if (typeof localStorage !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored && themes[stored]) {
      return stored
    }
  }
  return 'oled'
}

function createThemeStore() {
  const { subscribe, set } = writable(getInitialTheme())

  return {
    subscribe,
    setTheme: (themeName) => {
      if (themes[themeName]) {
        set(themeName)
        if (typeof localStorage !== 'undefined') {
          localStorage.setItem(STORAGE_KEY, themeName)
        }
        applyTheme(themeName)
      }
    }
  }
}

function applyTheme(themeName) {
  const theme = themes[themeName]
  if (!theme) return

  const root = document.documentElement
  Object.entries(theme.colors).forEach(([key, value]) => {
    root.style.setProperty(`--${key}`, value)
  })

  if (themeName === 'light') {
    root.classList.add('light-theme')
  } else {
    root.classList.remove('light-theme')
  }
}

export const currentTheme = createThemeStore()

if (typeof window !== 'undefined') {
  applyTheme(getInitialTheme())
}
