<script>
  import { createEventDispatcher } from 'svelte'
  import { processFiles, getSettings } from '../lib/api.js'

  const dispatch = createEventDispatcher()

  export let selectedFiles = []
  export let metadataProvider = 'omdb'
  export let disabled = false

  let processing = false
  let showConfirmation = false
  let duration = 40
  let results = null
  let error = null

  async function handleProcessClick() {
    if (selectedFiles.length === 0) {
      error = 'No files selected'
      return
    }

    try {
      const settings = await getSettings()
      duration = settings.duration ?? 40
    } catch (err) {
      console.error('Failed to load duration:', err)
    }

    showConfirmation = true
    error = null
  }

  async function confirmProcess() {
    processing = true
    showConfirmation = false
    error = null
    results = null

    try {
      const response = await processFiles(selectedFiles, duration)
      results = response.results
      dispatch('complete', { results })
    } catch (err) {
      error = `Processing failed: ${err.message}`
    } finally {
      processing = false
    }
  }

  function cancelProcess() {
    showConfirmation = false
  }

  function closeResults() {
    results = null
  }

  function formatMetadataLabel(source) {
    if (source === 'both') return 'OMDb + TMDb'
    if (source === 'tvmaze') return 'TVmaze'
    return source.toUpperCase()
  }

  $: successCount = results?.filter(r => r.success).length || 0
  $: failureCount = results?.filter(r => !r.success).length || 0
</script>

<div class="border-t border-border pt-10 mt-12">
  <div class="flex items-center gap-3">
    <button
      on:click={handleProcessClick}
      disabled={disabled || processing || selectedFiles.length === 0}
      class="px-7 py-3.5 bg-white hover:bg-white/90 disabled:opacity-30 disabled:cursor-not-allowed
             text-black text-[13px] font-medium rounded-xl transition-all"
    >
      {#if processing}
        Processing...
      {:else}
        Add Subtitles ({selectedFiles.length})
      {/if}
    </button>
  </div>

  {#if error}
    <div class="mt-6 px-5 py-4 bg-red-500/5 border border-red-500/20 rounded-xl">
      <p class="text-[13px] text-red-300">{error}</p>
    </div>
  {/if}
</div>

<!-- Confirmation Modal -->
{#if showConfirmation}
  <div class="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4" on:click={cancelProcess} role="button" tabindex="-1" on:keydown={(e) => e.key === 'Escape' && cancelProcess()}>
    <div class="bg-bg-card border border-border rounded-2xl p-8 max-w-md w-full" on:click|stopPropagation role="dialog" tabindex="-1" on:keydown>
      <h3 class="text-base font-medium mb-4">Confirm Processing</h3>
      <p class="text-[13px] text-text-secondary mb-2 leading-relaxed">
        Add plot summaries to {selectedFiles.length} {selectedFiles.length !== 1 ? 'files' : 'file'}
      </p>
      <p class="text-[11px] text-text-tertiary mb-6">
        Using <span class="text-white font-medium">{formatMetadataLabel(metadataProvider)}</span> as metadata source
      </p>
      <div class="px-4 py-3 bg-yellow-500/5 border border-yellow-500/20 rounded-xl mb-8">
        <p class="text-[11px] text-yellow-200">Files will be modified. Backups created automatically.</p>
      </div>
      <div class="flex gap-3 justify-end">
        <button
          on:click={cancelProcess}
          class="px-5 py-2.5 text-text-secondary hover:text-white text-[13px] transition-colors"
        >
          Cancel
        </button>
        <button
          on:click={confirmProcess}
          class="px-5 py-2.5 bg-white hover:bg-white/90 text-black text-[13px] font-medium rounded-xl transition-all"
        >
          Confirm
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Results Modal -->
{#if results}
  <div class="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4" on:click={closeResults} role="button" tabindex="-1" on:keydown={(e) => e.key === 'Escape' && closeResults()}>
    <div class="bg-bg-card border border-border rounded-2xl p-8 max-w-2xl w-full max-h-[80vh] overflow-y-auto" on:click|stopPropagation role="dialog" tabindex="-1" on:keydown>
      <h3 class="text-base font-medium mb-6">Results</h3>

      <div class="grid grid-cols-2 gap-4 mb-6">
        <div class="bg-green-500/5 border border-green-500/20 rounded-xl p-5 text-center">
          <div class="text-2xl font-semibold text-green-300">{successCount}</div>
          <div class="text-[11px] text-text-secondary mt-2 uppercase tracking-wide">Successful</div>
        </div>
        <div class="bg-red-500/5 border border-red-500/20 rounded-xl p-5 text-center">
          <div class="text-2xl font-semibold text-red-300">{failureCount}</div>
          <div class="text-[11px] text-text-secondary mt-2 uppercase tracking-wide">Failed</div>
        </div>
      </div>

      <div class="border border-border rounded-xl divide-y divide-border max-h-60 overflow-y-auto mb-6">
        {#each results as result}
          <div class="px-5 py-4 {result.success ? 'bg-green-500/5' : 'bg-red-500/5'}">
            <div class="text-[13px] truncate font-medium">{result.file.split(/[/\\]/).pop()}</div>
            <div class="text-[11px] text-text-tertiary mt-1">{result.success ? result.status : result.error || 'Failed'}</div>
          </div>
        {/each}
      </div>

      <button
        on:click={closeResults}
        class="px-7 py-3.5 bg-white hover:bg-white/90 text-black text-[13px] font-medium rounded-xl transition-all"
      >
        Close
      </button>
    </div>
  </div>
{/if}
