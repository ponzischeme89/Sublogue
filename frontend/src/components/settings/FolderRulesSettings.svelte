<script>
  import { onMount } from 'svelte'
  import { getFolderRules, saveFolderRule, deleteFolderRule } from '../../lib/api.js'
  import { addToast } from '../../lib/toastStore.js'

  export let settings = {}

  let rules = []
  let loading = false
  let error = null
  let editingDirectory = null

  let directory = ''
  let preferredSource = settings.preferred_source || 'omdb'
  let insertionPosition = settings.insertion_position || 'start'
  let language = ''
  let titleBold = settings.subtitle_title_bold !== false
  let plotItalic = settings.subtitle_plot_italic !== false
  let showDirector = settings.subtitle_show_director === true
  let showActors = settings.subtitle_show_actors === true
  let showReleased = settings.subtitle_show_released === true
  let showGenre = settings.subtitle_show_genre === true

  const sourceOptions = [
    { value: 'omdb', label: 'OMDb' },
    { value: 'tmdb', label: 'TMDb' },
    { value: 'tvmaze', label: 'TVmaze' },
    { value: 'wikipedia', label: 'Wikipedia' },
    { value: 'both', label: 'OMDb + TMDb' }
  ]

  function resetForm() {
    editingDirectory = null
    directory = ''
    preferredSource = settings.preferred_source || 'omdb'
    insertionPosition = settings.insertion_position || 'start'
    language = ''
    titleBold = settings.subtitle_title_bold !== false
    plotItalic = settings.subtitle_plot_italic !== false
    showDirector = settings.subtitle_show_director === true
    showActors = settings.subtitle_show_actors === true
    showReleased = settings.subtitle_show_released === true
    showGenre = settings.subtitle_show_genre === true
  }

  async function loadRules() {
    loading = true
    error = null
    try {
      const result = await getFolderRules()
      rules = result.rules || []
    } catch (err) {
      error = `Failed to load folder rules: ${err.message}`
    } finally {
      loading = false
    }
  }

  onMount(loadRules)

  function editRule(rule) {
    editingDirectory = rule.directory
    directory = rule.directory
    preferredSource = rule.preferred_source || settings.preferred_source || 'omdb'
    insertionPosition = rule.insertion_position || settings.insertion_position || 'start'
    language = rule.language || ''
    titleBold = rule.subtitle_title_bold ?? (settings.subtitle_title_bold !== false)
    plotItalic = rule.subtitle_plot_italic ?? (settings.subtitle_plot_italic !== false)
    showDirector = rule.subtitle_show_director ?? (settings.subtitle_show_director === true)
    showActors = rule.subtitle_show_actors ?? (settings.subtitle_show_actors === true)
    showReleased = rule.subtitle_show_released ?? (settings.subtitle_show_released === true)
    showGenre = rule.subtitle_show_genre ?? (settings.subtitle_show_genre === true)
  }

  async function saveRule() {
    if (!directory.trim()) {
      error = 'Directory is required'
      return
    }

    try {
      await saveFolderRule({
        directory: directory.trim(),
        preferred_source: preferredSource,
        insertion_position: insertionPosition,
        language: language.trim() || null,
        subtitle_title_bold: titleBold,
        subtitle_plot_italic: plotItalic,
        subtitle_show_director: showDirector,
        subtitle_show_actors: showActors,
        subtitle_show_released: showReleased,
        subtitle_show_genre: showGenre
      })
      addToast({ message: 'Folder rule saved.', tone: 'success' })
      await loadRules()
      resetForm()
    } catch (err) {
      error = `Failed to save folder rule: ${err.message}`
      addToast({ message: error, tone: 'error' })
    }
  }

  async function removeRule(rule) {
    try {
      await deleteFolderRule(rule.directory)
      addToast({ message: 'Folder rule removed.', tone: 'success' })
      await loadRules()
      if (editingDirectory === rule.directory) {
        resetForm()
      }
    } catch (err) {
      error = `Failed to delete folder rule: ${err.message}`
      addToast({ message: error, tone: 'error' })
    }
  }
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-lg font-semibold text-text-primary">Per-folder rules</h2>
    <p class="text-[13px] text-text-secondary">
      Override metadata source and subtitle formatting per directory.
    </p>
  </div>

  {#if error}
    <div class="px-5 py-4 bg-red-500/5 border border-red-500/20 rounded-xl">
      <p class="text-[13px] text-red-300">{error}</p>
    </div>
  {/if}

  <div class="rounded-xl border border-border bg-bg-secondary/40 p-5 space-y-4">
    <div class="grid gap-4 md:grid-cols-2">
      <div class="space-y-2">
        <label class="block text-[12px] text-text-tertiary uppercase tracking-wide">Directory</label>
        <input
          type="text"
          bind:value={directory}
          placeholder="C:\\Movies"
          class="w-full px-4 py-3 bg-bg-card border border-border rounded-lg text-[13px] font-mono focus:outline-none focus:border-white/25 focus:ring-2 focus:ring-ring transition-all"
        />
      </div>
      <div class="space-y-2">
        <label class="block text-[12px] text-text-tertiary uppercase tracking-wide">Metadata source</label>
        <select
          bind:value={preferredSource}
          class="w-full px-4 py-3 bg-bg-card border border-border rounded-lg text-[13px] focus:outline-none focus:border-white/25 focus:ring-2 focus:ring-ring transition-all"
        >
          {#each sourceOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </div>
    </div>

    <div class="grid gap-4 md:grid-cols-2">
      <div class="space-y-2">
        <label class="block text-[12px] text-text-tertiary uppercase tracking-wide">Insertion position</label>
        <select
          bind:value={insertionPosition}
          class="w-full px-4 py-3 bg-bg-card border border-border rounded-lg text-[13px] focus:outline-none focus:border-white/25 focus:ring-2 focus:ring-ring transition-all"
        >
          <option value="start">Start</option>
          <option value="end">End</option>
          <option value="index">Index 1</option>
        </select>
      </div>
      <div class="space-y-2">
        <label class="block text-[12px] text-text-tertiary uppercase tracking-wide">
          Language (TMDb)
        </label>
        <input
          type="text"
          bind:value={language}
          placeholder="it-IT"
          class="w-full px-4 py-3 bg-bg-card border border-border rounded-lg text-[13px] font-mono focus:outline-none focus:border-white/25 focus:ring-2 focus:ring-ring transition-all"
        />
        <p class="text-[11px] text-text-tertiary">
          Used for TMDb localized plots (e.g. it-IT, fr-FR). OMDb is always English.
        </p>
      </div>
    </div>

    <div class="grid gap-3 md:grid-cols-2">
      <label class="flex items-center justify-between gap-3 rounded-xl border border-border bg-bg-card px-4 py-3">
        <div class="text-[13px] font-medium">Bold Title</div>
        <input type="checkbox" bind:checked={titleBold} class="h-4 w-4" />
      </label>
      <label class="flex items-center justify-between gap-3 rounded-xl border border-border bg-bg-card px-4 py-3">
        <div class="text-[13px] font-medium">Italic Plot</div>
        <input type="checkbox" bind:checked={plotItalic} class="h-4 w-4" />
      </label>
      <label class="flex items-center justify-between gap-3 rounded-xl border border-border bg-bg-card px-4 py-3">
        <div class="text-[13px] font-medium">Director</div>
        <input type="checkbox" bind:checked={showDirector} class="h-4 w-4" />
      </label>
      <label class="flex items-center justify-between gap-3 rounded-xl border border-border bg-bg-card px-4 py-3">
        <div class="text-[13px] font-medium">Cast</div>
        <input type="checkbox" bind:checked={showActors} class="h-4 w-4" />
      </label>
      <label class="flex items-center justify-between gap-3 rounded-xl border border-border bg-bg-card px-4 py-3">
        <div class="text-[13px] font-medium">Release Date</div>
        <input type="checkbox" bind:checked={showReleased} class="h-4 w-4" />
      </label>
      <label class="flex items-center justify-between gap-3 rounded-xl border border-border bg-bg-card px-4 py-3">
        <div class="text-[13px] font-medium">Genre</div>
        <input type="checkbox" bind:checked={showGenre} class="h-4 w-4" />
      </label>
    </div>

    <div class="flex flex-wrap gap-3">
      <button
        type="button"
        on:click={saveRule}
        class="px-5 py-2.5 bg-white text-black text-[13px] font-medium rounded-lg hover:bg-white/90 transition-all"
      >
        {editingDirectory ? 'Update rule' : 'Add rule'}
      </button>
      {#if editingDirectory}
        <button
          type="button"
          on:click={resetForm}
          class="px-5 py-2.5 text-text-secondary text-[13px] rounded-lg border border-border hover:text-white hover:bg-bg-hover transition-all"
        >
          Cancel
        </button>
      {/if}
    </div>
  </div>

  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <h3 class="text-[13px] font-semibold text-text-primary">Active rules</h3>
      <button
        type="button"
        on:click={loadRules}
        class="text-[12px] text-text-tertiary hover:text-white transition-colors"
      >
        Refresh
      </button>
    </div>

    {#if loading}
      <div class="text-[12px] text-text-tertiary">Loading rules...</div>
    {:else if rules.length === 0}
      <div class="rounded-xl border border-border bg-bg-secondary/30 px-4 py-4 text-[12px] text-text-tertiary">
        No folder rules yet.
      </div>
    {:else}
      <div class="space-y-3">
        {#each rules as rule}
          <div class="rounded-xl border border-border bg-bg-secondary/30 px-4 py-3 flex flex-col gap-2">
            <div class="flex items-start justify-between gap-3">
              <div>
                <div class="text-[13px] font-medium text-text-primary">{rule.directory}</div>
                <div class="text-[11px] text-text-tertiary">
                  {rule.preferred_source || settings.preferred_source || 'omdb'} ·
                  {rule.insertion_position || settings.insertion_position || 'start'} ·
                  {rule.language || 'default language'}
                </div>
              </div>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  on:click={() => editRule(rule)}
                  class="text-[12px] text-text-secondary hover:text-white transition-colors"
                >
                  Edit
                </button>
                <button
                  type="button"
                  on:click={() => removeRule(rule)}
                  class="text-[12px] text-red-300 hover:text-red-200 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>
