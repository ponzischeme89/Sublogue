import { writable } from 'svelte/store'

// Simple in-memory store for scan results
// No localStorage to avoid performance issues
function createScanStore() {
  const { subscribe, set, update } = writable({
    files: [],
    lastScan: null,
    directory: ''
  })

  return {
    subscribe,
    setScanResults: (files, directory) => {
      update(state => ({
        ...state,
        files,
        directory,
        lastScan: new Date().toISOString()
      }))
    },
    clearResults: () => {
      set({
        files: [],
        lastScan: null,
        directory: ''
      })
    }
  }
}

export const scanResults = createScanStore()
