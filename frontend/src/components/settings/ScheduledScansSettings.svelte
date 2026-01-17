<script>
  import { onMount } from 'svelte'
  import { Button } from '../../lib/components/ui/button'
  import { Input } from '../../lib/components/ui/input'
  import { createScheduledScan } from '../../lib/api.js'
  import { addToast } from '../../lib/toastStore.js'

  export let settings = {}

  let directory = settings.default_directory || ''
  let scheduledFor = ''
  let creating = false
  let error = null
  let successMessage = null

  function getLocalDateTimeValue(date) {
    const pad = (value) => String(value).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
      date.getDate()
    )}T${pad(date.getHours())}:${pad(date.getMinutes())}`
  }

  async function scheduleScan() {
    if (!directory || !scheduledFor) {
      error = 'Please choose a directory and scheduled time'
      successMessage = null
      return
    }
    creating = true
    error = null
    try {
      const scheduledIso = new Date(scheduledFor).toISOString()
      await createScheduledScan(directory, scheduledIso)
      successMessage = 'Scan scheduled. Track results in Scheduled Scans.'
      addToast({ message: 'Scheduled scan created.', tone: 'success' })
    } catch (err) {
      error = `Failed to schedule scan: ${err.message}`
      addToast({ message: error, tone: 'error' })
    } finally {
      creating = false
    }
  }

  onMount(() => {
    const nextHour = new Date()
    nextHour.setHours(nextHour.getHours() + 1)
    scheduledFor = getLocalDateTimeValue(nextHour)
  })
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-lg font-semibold text-text-primary">Scheduled Scans</h2>
    <p class="text-[13px] text-text-secondary">
      Plan scans ahead of time and let them run in the background.
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

  <div class="rounded-xl border border-border bg-card p-6 space-y-4">
    <div>
      <h3 class="text-sm font-semibold text-text-primary">Schedule a scan</h3>
      <p class="text-[12px] text-text-tertiary">
        Use your default directory or customize a one-off scan target.
      </p>
    </div>

    <div class="grid gap-4 sm:grid-cols-2">
      <div class="space-y-2">
        <label class="block text-[12px] font-medium text-text-primary">
          Directory
        </label>
        <Input
          type="text"
          bind:value={directory}
          placeholder="C:\Movies or /media/movies"
          className="h-10 text-[12px] font-mono"
        />
        <p class="text-[11px] text-text-tertiary">
          Default directory comes from General Settings.
        </p>
      </div>
      <div class="space-y-2">
        <label class="block text-[12px] font-medium text-text-primary">
          Scheduled for
        </label>
        <Input
          type="datetime-local"
          bind:value={scheduledFor}
          className="h-10 text-[12px]"
        />
        <p class="text-[11px] text-text-tertiary">
          Scheduled scans run once at the chosen time.
        </p>
      </div>
    </div>

    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <p class="text-[11px] text-text-tertiary">
        Results show in Scheduled Scans and the History tab.
      </p>
      <Button
        size="sm"
        className="h-9 px-4"
        on:click={scheduleScan}
        disabled={creating}
      >
        {creating ? 'Scheduling...' : 'Schedule Scan'}
      </Button>
    </div>
  </div>
</div>
