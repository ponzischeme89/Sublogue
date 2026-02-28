import { writable } from 'svelte/store'

export const themes = {
  oled: {
    name: 'Midnight',
    colors: {
      // Midnight backgrounds — sophisticated dark, not pure black
      'bg-primary': '#0d0e11',
      'bg-secondary': '#13141a',
      'bg-card': '#17181f',
      'bg-hover': '#1e2028',

      // Text — slightly warm off-white with clear hierarchy
      'text-primary': '#edeef3',
      'text-secondary': '#888ba8',
      'text-tertiary': '#50526b',

      // UI chrome
      'border': 'rgba(255, 255, 255, 0.08)',

      // Accents & interaction
      'accent': '#a5b4fc',              // soft indigo for links/highlights
      'button-bg': '#1a1b22',
      'button-hover': '#1e2028',
      'button-text': '#edeef3',
      'focus-ring': 'rgba(165, 180, 252, 0.35)',
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
      'border': 'rgba(120, 170, 220, 0.15)',

      // Accents & interaction
      'accent': '#5fa8ff',                  // beautiful ocean blue
      'button-bg': '#132646',
      'button-hover': '#1b3560',
      'button-text': '#eaf3ff',
      'focus-ring': 'rgba(95, 168, 255, 0.4)',
    }
  },

  light: {
    name: 'Light',
    colors: {
      'bg-primary': '#f6f7f9',
      'bg-secondary': '#eef0f3',
      'bg-card': '#ffffff',
      'bg-hover': '#e8eaee',

      'text-primary': '#111318',
      'text-secondary': '#5c5f73',
      'text-tertiary': '#9094aa',

      'border': 'rgba(0, 0, 0, 0.08)',

      'accent': '#4f46e5',               // indigo accent
      'button-bg': '#ffffff',
      'button-hover': '#f0f1f5',
      'button-text': '#111318',
      'focus-ring': 'rgba(79, 70, 229, 0.3)',
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
