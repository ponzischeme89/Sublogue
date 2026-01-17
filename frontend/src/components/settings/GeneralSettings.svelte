<script>
  export let settings = {};
  export let saving = false;
  export let onSave;

  let defaultDirectory = settings.default_directory || '';
  let duration = settings.duration ?? 40;
  let insertionPosition = settings.insertion_position || 'start';
  let quoteStyle = settings.quote_style || 'sarcastic';

  // Subtitle formatting options
  let titleBold = settings.subtitle_title_bold !== false;
  let plotItalic = settings.subtitle_plot_italic !== false;
  let showDirector = settings.subtitle_show_director === true;
  let showActors = settings.subtitle_show_actors === true;
  let showReleased = settings.subtitle_show_released === true;
  let showGenre = settings.subtitle_show_genre === true;
  let showPreview = false;

  function handleSubmit() {
    onSave({
      default_directory: defaultDirectory,
      duration: parseInt(duration),
      insertion_position: insertionPosition,
      quote_style: quoteStyle,
      subtitle_title_bold: titleBold,
      subtitle_plot_italic: plotItalic,
      subtitle_show_director: showDirector,
      subtitle_show_actors: showActors,
      subtitle_show_released: showReleased,
      subtitle_show_genre: showGenre
    });
  }
</script>

<form on:submit|preventDefault={handleSubmit} class="space-y-8">
  <div>
      <h2 class="text-lg font-semibold text-text-primary">General Settings</h2>
    <p class="text-[13px] text-text-secondary mb-6">
      Control how scans run and where summaries are placed.
    </p>

    <div class="space-y-6">
      <div class="space-y-3">
        <label for="directory" class="block text-[13px] font-medium text-text-primary">
          Default Directory
        </label>
        <input
          id="directory"
          type="text"
          bind:value={defaultDirectory}
          placeholder="C:\Movies"
          class="w-full px-4 py-3.5 bg-bg-card border border-border rounded-xl
                 text-[13px] font-mono placeholder:text-text-tertiary
                 focus:outline-none focus:border-white/25 focus:ring-2 focus:ring-ring transition-all"
        />
        <p class="text-[12px] text-text-secondary">
          Default directory to scan for subtitle files
        </p>
      </div>

      <div class="space-y-3">
        <label class="block text-[13px] font-medium text-text-primary">
          Subtitle Item Duration
        </label>
        <div class="flex flex-wrap gap-2">
          {#each [
            { value: 0, label: 'Auto', desc: 'Smart' },
            { value: 15, label: '15s', desc: 'Quick' },
            { value: 30, label: '30s', desc: 'Short' },
            { value: 45, label: '45s', desc: 'Standard' },
            { value: 60, label: '60s', desc: 'Extended' },
            { value: 90, label: '90s', desc: 'Long' }
          ] as preset}
            <button
              type="button"
              on:click={() => duration = preset.value}
              class="px-3 py-1.5 rounded-full text-[12px] font-medium transition-all border
                     {duration === preset.value
                       ? 'bg-text-primary text-bg-primary border-white'
                       : 'bg-bg-card text-text-secondary hover:bg-bg-hover hover:text-text-primary border-border'}"
            >
              {preset.label}
            </button>
          {/each}
        </div>
        <p class="text-[12px] text-text-secondary">
          Sets the target duration per generated subtitle item. Auto lets Sublogue choose based on reading speed.
        </p>
      </div>

      <div class="space-y-3">
        <label class="block text-[13px] font-medium text-text-primary">
          Insertion Position
        </label>
        <div class="grid grid-cols-3 gap-2">
          <button
            type="button"
            on:click={() => insertionPosition = 'start'}
            class="flex flex-col items-center gap-1 px-3 py-2.5 rounded-xl text-center transition-all border
                   {insertionPosition === 'start'
                     ? 'bg-text-primary text-bg-primary border-white'
                     : 'bg-bg-card text-text-secondary hover:bg-bg-hover border-border'}"
          >
            <span class="text-[12px] font-medium">Start</span>
            <span class="text-[10px] {insertionPosition === 'start' ? 'text-bg-primary/70' : 'text-text-tertiary'}">Before all subs</span>
          </button>
          <button
            type="button"
            on:click={() => insertionPosition = 'end'}
            class="flex flex-col items-center gap-1 px-3 py-2.5 rounded-xl text-center transition-all border
                   {insertionPosition === 'end'
                     ? 'bg-text-primary text-bg-primary border-white'
                     : 'bg-bg-card text-text-secondary hover:bg-bg-hover border-border'}"
          >
            <span class="text-[12px] font-medium">End</span>
            <span class="text-[10px] {insertionPosition === 'end' ? 'text-bg-primary/70' : 'text-text-tertiary'}">After credits</span>
          </button>
          <button
            type="button"
            on:click={() => insertionPosition = 'index'}
            class="flex flex-col items-center gap-1 px-3 py-2.5 rounded-xl text-center transition-all border
                   {insertionPosition === 'index'
                     ? 'bg-text-primary text-bg-primary border-white'
                     : 'bg-bg-card text-text-secondary hover:bg-bg-hover border-border'}"
          >
            <span class="text-[12px] font-medium">Index 1</span>
            <span class="text-[10px] {insertionPosition === 'index' ? 'text-bg-primary/70' : 'text-text-tertiary'}">First position</span>
          </button>
        </div>
        <p class="text-[12px] text-text-secondary">
          Where to insert the plot summary in the subtitle file
        </p>
      </div>

      <div class="space-y-3">
        <label class="block text-[13px] font-medium text-text-primary">
          Waiting Quote Style
        </label>
        <div class="flex gap-2">
          <button
            type="button"
            on:click={() => quoteStyle = 'sarcastic'}
            class="flex-1 px-4 py-3 rounded-lg text-[13px] font-medium transition-all border
                   {quoteStyle === 'sarcastic'
                     ? 'bg-text-primary text-bg-primary border-white shadow-[0_1px_3px_rgba(0,0,0,0.3)]'
                     : 'bg-bg-card text-text-secondary hover:bg-bg-hover hover:text-text-primary border-border'}"
          >
            Sarcastic
          </button>
          <button
            type="button"
            on:click={() => quoteStyle = 'rude'}
            class="flex-1 px-4 py-3 rounded-lg text-[13px] font-medium transition-all border
                   {quoteStyle === 'rude'
                     ? 'bg-text-primary text-bg-primary border-white shadow-[0_1px_3px_rgba(0,0,0,0.3)]'
                     : 'bg-bg-card text-text-secondary hover:bg-bg-hover hover:text-text-primary border-border'}"
          >
            Rude
          </button>
          <button
            type="button"
            on:click={() => quoteStyle = 'nice'}
            class="flex-1 px-4 py-3 rounded-lg text-[13px] font-medium transition-all border
                   {quoteStyle === 'nice'
                     ? 'bg-text-primary text-bg-primary border-white shadow-[0_1px_3px_rgba(0,0,0,0.3)]'
                     : 'bg-bg-card text-text-secondary hover:bg-bg-hover hover:text-text-primary border-border'}"
          >
            Nice
          </button>
        </div>
        <p class="text-[12px] text-text-secondary">
          Tone of random quotes shown while waiting for scans
        </p>
      </div>

    </div>
  </div>

  <!-- Subtitle Formatting Section -->
  <div>
    <h2 class="text-lg font-semibold text-text-primary">Subtitle Formatting</h2>
    <p class="text-[13px] text-text-secondary mb-6">
      Tune how metadata appears inside subtitle headers.
    </p>

    <div class="space-y-6">
      <!-- Text Styling -->
      <div class="space-y-3">
        <label class="block text-[13px] font-medium mb-3 text-text-primary">Text Styling</label>

        <label class="flex items-center justify-between gap-4 rounded-xl border border-border bg-bg-secondary/40 px-4 py-3">
          <div>
            <div class="text-[13px] font-medium">Bold Title</div>
            <div class="text-[11px] text-text-tertiary mt-0.5">
              Display movie title in <strong>bold</strong> text
            </div>
          </div>
          <span class="relative inline-flex items-center">
            <input type="checkbox" bind:checked={titleBold} class="sr-only peer" />
            <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
            <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
          </span>
        </label>

        <label class="flex items-center justify-between gap-4 rounded-xl border border-border bg-bg-secondary/40 px-4 py-3">
          <div>
            <div class="text-[13px] font-medium">Italic Plot</div>
            <div class="text-[11px] text-text-tertiary mt-0.5">
              Display plot summary in <em>italic</em> text
            </div>
          </div>
          <span class="relative inline-flex items-center">
            <input type="checkbox" bind:checked={plotItalic} class="sr-only peer" />
            <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
            <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
          </span>
        </label>
      </div>

      <!-- Additional Info -->
      <div class="space-y-3">
        <label class="block text-[13px] font-medium mb-3 text-text-primary">Additional Information</label>
        <p class="text-[12px] text-text-secondary -mt-2 mb-3">
          Show extra metadata in the subtitle header
        </p>

        <label class="flex items-center justify-between gap-4 rounded-xl border border-border bg-bg-secondary/40 px-4 py-3">
          <div class="text-[13px] font-medium">Director</div>
          <span class="relative inline-flex items-center">
            <input type="checkbox" bind:checked={showDirector} class="sr-only peer" />
            <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
            <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
          </span>
        </label>

        <label class="flex items-center justify-between gap-4 rounded-xl border border-border bg-bg-secondary/40 px-4 py-3">
          <div class="text-[13px] font-medium">Cast</div>
          <span class="relative inline-flex items-center">
            <input type="checkbox" bind:checked={showActors} class="sr-only peer" />
            <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
            <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
          </span>
        </label>

        <label class="flex items-center justify-between gap-4 rounded-xl border border-border bg-bg-secondary/40 px-4 py-3">
          <div class="text-[13px] font-medium">Release Date</div>
          <span class="relative inline-flex items-center">
            <input type="checkbox" bind:checked={showReleased} class="sr-only peer" />
            <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
            <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
          </span>
        </label>

        <label class="flex items-center justify-between gap-4 rounded-xl border border-border bg-bg-secondary/40 px-4 py-3">
          <div class="text-[13px] font-medium">Genre</div>
          <span class="relative inline-flex items-center">
            <input type="checkbox" bind:checked={showGenre} class="sr-only peer" />
            <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
            <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
          </span>
        </label>
      </div>
    </div>
  </div>

  <div class="rounded-xl border border-border bg-bg-secondary/30 p-6 space-y-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h3 class="text-sm font-semibold text-text-primary">Preview formatting</h3>
        <p class="text-[12px] text-text-tertiary">
          Preview how the header and plot will look with your current choices.
        </p>
      </div>
      <button
        type="button"
        on:click={() => (showPreview = !showPreview)}
        class="px-4 py-2 rounded-lg border border-border text-[12px] text-text-secondary hover:text-white hover:bg-bg-hover transition-all"
      >
        {showPreview ? 'Hide preview' : 'Show preview'}
      </button>
    </div>

    {#if showPreview}
      <div class="rounded-xl border border-border bg-bg-card p-4 text-[12px] text-text-secondary space-y-3">
        <div class="space-y-1">
          <div class="text-text-primary">
            {#if titleBold}
              <strong>Sample Movie (2024)</strong>
            {:else}
              Sample Movie (2024)
            {/if}
          </div>
          <div class="text-text-tertiary">IMDb: 7.8 • RT: 91% • 118 min</div>
          {#if showDirector}
            <div>Director: Jane Doe</div>
          {/if}
          {#if showActors}
            <div>Cast: Alex Actor, Casey Star, Morgan Lee</div>
          {/if}
          {#if showReleased}
            <div>Release Date: May 12, 2024</div>
          {/if}
          {#if showGenre}
            <div>Genre: Drama, Sci-Fi</div>
          {/if}
        </div>
        <div class="border-t border-border pt-3 text-text-secondary">
          {#if plotItalic}
            <em>Plot: A calm AI awakens in a distant archive and learns to rewrite forgotten stories.</em>
          {:else}
            Plot: A calm AI awakens in a distant archive and learns to rewrite forgotten stories.
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <button
    type="submit"
    disabled={saving}
    class="px-7 py-3.5 bg-text-primary hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed
           text-bg-primary text-[13px] font-medium rounded-xl transition-all"
  >
    {saving ? 'Saving...' : 'Save Changes'}
  </button>
</form>
