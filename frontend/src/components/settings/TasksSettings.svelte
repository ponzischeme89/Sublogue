<script>
  import { Button } from '../../lib/components/ui/button'
  import { resetSettings, clearHistory, clearCaches } from '../../lib/api.js'
  import { scanResults } from '../../lib/scanStore.js'
  import { addToast } from '../../lib/toastStore.js'

  let keepApiKeys = true
  let runningReset = false
  let runningHistory = false
  let runningCaches = false
  let error = null
  let successMessage = null

  function resetMessages() {
    error = null
    successMessage = null
  }

  async function handleResetSettings() {
    resetMessages()
    runningReset = true
    try {
      await resetSettings(keepApiKeys)
      successMessage = 'Settings cleared successfully.'
      addToast({ message: successMessage, tone: 'success' })
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem('sublogue_onboarding_complete')
      }
      scanResults.clearResults()
    } catch (err) {
      error = `Failed to clear settings: ${err.message}`
      addToast({ message: error, tone: 'error' })
    } finally {
      runningReset = false
    }
  }

  async function handleClearHistory() {
    resetMessages()
    runningHistory = true
    try {
      await clearHistory()
      successMessage = 'History and logs cleared.'
      addToast({ message: successMessage, tone: 'success' })
    } catch (err) {
      error = `Failed to clear history: ${err.message}`
      addToast({ message: error, tone: 'error' })
    } finally {
      runningHistory = false
    }
  }

  async function handleClearCaches() {
    resetMessages()
    runningCaches = true
    try {
      await clearCaches()
      successMessage = 'Caches cleared.'
      addToast({ message: successMessage, tone: 'success' })
    } catch (err) {
      error = `Failed to clear caches: ${err.message}`
      addToast({ message: error, tone: 'error' })
    } finally {
      runningCaches = false
    }
  }
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-lg font-semibold text-text-primary">Maintenance Tasks</h2>
    <p class="text-[13px] text-text-secondary">
      Run cleanup tasks to keep the app lean and reset state when needed.
    </p>
  </div>

  {#if error}
    <div class="px-5 py-4 bg-red-500/5 border border-red-500/20 rounded-xl">
      <p class="text-[13px] text-red-300">{error}</p>
    </div>
  {/if}

  {#if successMessage}
    <div class="px-5 py-4 bg-green-500/5 border border-green-500/20 rounded-xl">
      <p class="text-[13px] text-green-300">{successMessage}</p>
    </div>
  {/if}

  <div class="grid gap-4">
    <div class="rounded-xl border border-border bg-card p-6 space-y-4">
      <div>
        <h3 class="text-sm font-semibold text-text-primary">Clear history and logs</h3>
        <p class="text-[12px] text-text-tertiary">
          Removes processing runs, scan history, scheduled scans, and API usage logs.
        </p>
      </div>
      <div class="flex items-center justify-between">
        <p class="text-[11px] text-text-tertiary">
          Useful if you want a clean slate for reporting.
        </p>
        <Button
          size="sm"
          variant="outline"
          className="h-9 px-4"
          on:click={handleClearHistory}
          disabled={runningHistory}
        >
          {#if runningHistory}
            <span class="inline-flex items-center gap-2">
              <span class="h-3 w-3 rounded-full border border-white/60 border-t-transparent animate-spin"></span>
              Clearing...
            </span>
          {:else}
            Clear History
          {/if}
        </Button>
      </div>
    </div>

    <div class="rounded-xl border border-border bg-card p-6 space-y-4">
      <div>
        <h3 class="text-sm font-semibold text-text-primary">Clear caches</h3>
        <p class="text-[12px] text-text-tertiary">
          Clears cached matches and resets the current scan state.
        </p>
      </div>
      <div class="flex items-center justify-between">
        <p class="text-[11px] text-text-tertiary">
          Recommended after large directory changes.
        </p>
        <Button
          size="sm"
          variant="outline"
          className="h-9 px-4"
          on:click={handleClearCaches}
          disabled={runningCaches}
        >
          {#if runningCaches}
            <span class="inline-flex items-center gap-2">
              <span class="h-3 w-3 rounded-full border border-white/60 border-t-transparent animate-spin"></span>
              Clearing...
            </span>
          {:else}
            Clear Caches
          {/if}
        </Button>
      </div>
    </div>
  </div>

  <div class="rounded-xl border border-red-500/30 bg-red-500/5 p-6 space-y-4">
    <div>
      <h3 class="text-sm font-semibold text-red-200">Danger Zone</h3>
      <p class="text-[12px] text-red-200/70">
        Destructive actions that reset your configuration.
      </p>
    </div>

    <div class="rounded-xl border border-red-500/30 bg-bg-card/60 p-4 space-y-4">
      <div>
        <h4 class="text-[13px] font-semibold text-text-primary">Reset settings</h4>
        <p class="text-[12px] text-text-tertiary">
          Clears all saved settings and resets preferences to defaults.
        </p>
      </div>

      <label class="flex items-center justify-between gap-4 rounded-xl border border-border bg-bg-secondary/40 px-4 py-3 text-[12px] text-text-secondary">
        <span>Keep OMDb and TMDb API keys</span>
        <span class="relative inline-flex items-center">
          <input type="checkbox" bind:checked={keepApiKeys} class="sr-only peer" />
          <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
          <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
        </span>
      </label>

      <div class="flex items-center justify-between">
        <p class="text-[11px] text-text-tertiary">
          This does not delete scan history or logs.
        </p>
        <Button
          size="sm"
          variant="destructive"
          className="h-9 px-4"
          on:click={handleResetSettings}
          disabled={runningReset}
        >
          {#if runningReset}
            <span class="inline-flex items-center gap-2">
              <span class="h-3 w-3 rounded-full border border-white/60 border-t-transparent animate-spin"></span>
              Clearing...
            </span>
          {:else}
            Clear Settings
          {/if}
        </Button>
      </div>
    </div>
  </div>
</div>
