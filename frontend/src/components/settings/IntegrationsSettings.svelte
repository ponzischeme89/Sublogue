<script>
  import { onMount } from "svelte";
  import { getIntegrationUsage } from "../../lib/api.js";
  import { Info } from "lucide-svelte";

  export let settings = {};
  export let saving = false;
  export let onSave;

  let omdbApiKey = settings.omdb_api_key || settings.api_key || "";
  let tmdbApiKey = settings.tmdb_api_key || "";
  let omdbEnabled = settings.omdb_enabled ?? false;
  let tmdbEnabled = settings.tmdb_enabled ?? false;
  let tvmazeEnabled = settings.tvmaze_enabled ?? false;
  let usage = null;
  let loadingUsage = false;
  let showOmdbHelp = false;
  let showTmdbHelp = false;
  let showTvmazeHelp = false;

  /* ===============================
     Lifecycle
     =============================== */

  onMount(async () => {
    await loadUsage();
  });

  function toggleOmdbHelp() {
    showOmdbHelp = !showOmdbHelp;
    if (showOmdbHelp) {
      showTmdbHelp = false;
    }
  }

  function toggleTmdbHelp() {
    showTmdbHelp = !showTmdbHelp;
    if (showTmdbHelp) {
      showOmdbHelp = false;
    }
  }

  function toggleTvmazeHelp() {
    showTvmazeHelp = !showTvmazeHelp;
    if (showTvmazeHelp) {
      showOmdbHelp = false;
      showTmdbHelp = false;
    }
  }

  function clickOutside(node, handler) {
    if (typeof handler !== "function") return { destroy() {} };
    const onPointerDown = (event) => {
      if (!node.contains(event.target)) handler(event);
    };
    document.addEventListener("mousedown", onPointerDown, true);
    document.addEventListener("touchstart", onPointerDown, true);
    return {
      destroy() {
        document.removeEventListener("mousedown", onPointerDown, true);
        document.removeEventListener("touchstart", onPointerDown, true);
      },
    };
  }

  async function loadUsage() {
    loadingUsage = true;
    try {
      const response = await getIntegrationUsage();
      usage = response.usage;
    } catch (err) {
      console.error("Failed to load usage stats:", err);
    } finally {
      loadingUsage = false;
    }
  }

  function handleSubmit() {
    onSave({
      omdb_api_key: omdbApiKey,
      tmdb_api_key: tmdbApiKey,
      omdb_enabled: omdbEnabled,
      tmdb_enabled: tmdbEnabled,
      tvmaze_enabled: tvmazeEnabled,
    });
  }

  /* ===============================
     Usage helpers
     =============================== */

  function usagePercent(current, limit) {
    if (!limit || limit <= 0) return 0;
    return Math.min(100, Math.round((current / limit) * 100));
  }

  function usageState(percent) {
    if (percent < 80) return "ok";
    if (percent < 95) return "warn";
    return "critical";
  }

  function usageBarColor(state) {
    if (state === "ok") return "bg-green-500";
    if (state === "warn") return "bg-yellow-500";
    return "bg-red-500";
  }

  function usageLabel(state) {
    if (state === "ok") return "OK";
    if (state === "warn") return "Warning";
    return "Critical";
  }

  function formatResetTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = date - now;

    if (diff <= 0) return "Now";

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  }

  /* ===============================
     Reactive usage values
     =============================== */

  $: omdbUsage = usage?.omdb;
  $: tmdbUsage = usage?.tmdb;
  $: tvmazeUsage = usage?.tvmaze;

  $: omdbPercent = omdbUsage
    ? usagePercent(omdbUsage.total_calls_24h, omdbUsage.limit)
    : 0;

  $: tmdbPercent = tmdbUsage
    ? usagePercent(tmdbUsage.total_calls_24h, tmdbUsage.limit)
    : 0;
  $: tvmazePercent = tvmazeUsage
    ? usagePercent(tvmazeUsage.total_calls_24h, tvmazeUsage.limit)
    : 0;

  $: omdbState = usageState(omdbPercent);
  $: tmdbState = usageState(tmdbPercent);
  $: tvmazeState = usageState(tvmazePercent);
  $: enabledCount =
    (omdbEnabled ? 1 : 0) + (tmdbEnabled ? 1 : 0) + (tvmazeEnabled ? 1 : 0);
</script>

<form on:submit|preventDefault={handleSubmit} class="space-y-8">
  <div>
    <h2 class="text-lg font-semibold text-text-primary">Integrations</h2>
    <p class="text-[13px] text-text-secondary mb-8">
      Connect services to fetch movie and TV metadata
    </p>

    {#if enabledCount === 0}
      <div class="mb-8 rounded-xl border border-border bg-bg-card p-6">
        <h3 class="text-[13px] font-medium text-text-primary mb-2">
          No integrations enabled
        </h3>
        <p class="text-[11px] text-text-tertiary mb-4">
          Add a provider to start fetching metadata.
        </p>
        <div class="flex flex-col sm:flex-row gap-3">
          <button
            type="button"
            class="px-4 py-2.5 rounded-lg border border-border bg-white/5 text-[12px] text-text-secondary hover:text-white hover:bg-bg-hover transition-colors"
            on:click={() => (omdbEnabled = true)}
          >
            Add OMDb
          </button>
          <button
            type="button"
            class="px-4 py-2.5 rounded-lg border border-border bg-white/5 text-[12px] text-text-secondary hover:text-white hover:bg-bg-hover transition-colors"
            on:click={() => (tmdbEnabled = true)}
          >
            Add TMDb
          </button>
          <button
            type="button"
            class="px-4 py-2.5 rounded-lg border border-border bg-white/5 text-[12px] text-text-secondary hover:text-white hover:bg-bg-hover transition-colors"
            on:click={() => (tvmazeEnabled = true)}
          >
            Add TVmaze
          </button>
        </div>
      </div>
    {/if}

    <div class="space-y-8">
      {#if enabledCount > 0}
        <div class="rounded-xl border border-border bg-bg-card p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <p class="text-[12px] font-medium text-text-primary">Add another integration</p>
            <p class="text-[11px] text-text-tertiary">Choose a provider to enable.</p>
          </div>
          <div class="flex flex-wrap gap-2">
            {#if !omdbEnabled}
              <button
                type="button"
                class="px-3 py-2 rounded-lg border border-border bg-white/5 text-[12px] text-text-secondary hover:text-white hover:bg-bg-hover transition-colors"
                on:click={() => (omdbEnabled = true)}
              >
                Add OMDb
              </button>
            {/if}
            {#if !tmdbEnabled}
              <button
                type="button"
                class="px-3 py-2 rounded-lg border border-border bg-white/5 text-[12px] text-text-secondary hover:text-white hover:bg-bg-hover transition-colors"
                on:click={() => (tmdbEnabled = true)}
              >
                Add TMDb
              </button>
            {/if}
            {#if !tvmazeEnabled}
              <button
                type="button"
                class="px-3 py-2 rounded-lg border border-border bg-white/5 text-[12px] text-text-secondary hover:text-white hover:bg-bg-hover transition-colors"
                on:click={() => (tvmazeEnabled = true)}
              >
                Add TVmaze
              </button>
            {/if}
          </div>
        </div>
      {/if}

      <!-- ===============================
           OMDb Integration
           =============================== -->
      {#if omdbEnabled}
      <div class="border border-border rounded-xl p-6 space-y-4">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h3 class="text-[13px] font-medium">OMDb API</h3>
            <p class="text-[11px] text-text-tertiary mt-1">
              The Open Movie Database - Movie and series metadata
            </p>
          </div>
          <div class="flex items-center gap-2">
            <div class="relative" use:clickOutside={() => (showOmdbHelp = false)}>
              <button
                type="button"
                class="h-8 w-8 rounded-full border border-border text-text-secondary hover:text-white hover:bg-bg-hover transition-all"
                on:click={toggleOmdbHelp}
                aria-label="How to get an OMDb API key"
              >
                <Info class="h-4 w-4 mx-auto" />
              </button>
              {#if showOmdbHelp}
                <div class="absolute right-0 mt-2 w-64 rounded-xl border border-border bg-bg-card p-4 text-[12px] text-text-secondary shadow-[0_12px_30px_rgba(0,0,0,0.35)] z-10">
                  <p class="text-[12px] text-text-primary font-medium mb-1">Get an OMDb API key</p>
                  <p class="text-[11px] text-text-tertiary mb-3">Create a free key in minutes.</p>
                  <ol class="space-y-1 text-[11px] text-text-secondary">
                    <li>Visit <a class="text-white hover:underline" href="https://www.omdbapi.com/apikey.aspx" target="_blank" rel="noopener noreferrer">omdbapi.com</a></li>
                    <li>Request a key and confirm the email</li>
                    <li>Paste the key here and save</li>
                  </ol>
                </div>
              {/if}
            </div>
            <span
              class="px-2 py-1 text-[10px] font-medium text-text-secondary border border-border rounded-lg uppercase tracking-wide"
            >
              Movies & Series
            </span>
          </div>
        </div>

        <div class="flex items-center justify-between gap-4 rounded-lg border border-border bg-bg-card px-4 py-3">
          <div>
            <p class="text-[12px] font-medium text-text-primary">Enable OMDb</p>
            <p class="text-[11px] text-text-tertiary">Use OMDb for movie and series metadata.</p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" class="sr-only peer" bind:checked={omdbEnabled} />
            <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
            <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
          </label>
        </div>

        <div class="space-y-2">
          <label
            class="block text-[11px] font-medium text-text-secondary uppercase tracking-wide"
          >
            API Key
          </label>

          <input
            type="text"
            bind:value={omdbApiKey}
            placeholder="Enter your OMDb API key"
            disabled={!omdbEnabled}
            class="w-full px-4 py-3 bg-bg-card border border-border rounded-lg
                   text-[13px] placeholder:text-text-tertiary
                   focus:outline-none focus:border-white/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          />
        </div>

        {#if omdbUsage && omdbEnabled}
          <div class="pt-4 border-t border-border space-y-2">
            <div class="flex items-center justify-between text-[11px]">
              <span class="text-text-secondary uppercase tracking-wide">
                {usageLabel(omdbState)} · Usage (24h)
              </span>
              <span class="text-text-tertiary">
                Resets in {formatResetTime(omdbUsage.reset_time)}
              </span>
            </div>

            <div class="space-y-1.5">
              <div class="flex items-center justify-between text-[11px]">
                <span class="text-text-tertiary">
                  {omdbUsage.total_calls_24h} / {omdbUsage.limit} calls
                </span>
                <span class="text-text-tertiary">
                  {omdbPercent}%
                </span>
              </div>

              <div
                class="relative h-3 bg-bg-primary rounded-full overflow-hidden"
              >
                <div
                  class="absolute inset-y-0 left-0 transition-all {usageBarColor(
                    omdbState,
                  )}"
                  style="width: {omdbPercent}%"
                ></div>

                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-[10px] font-medium text-black/80">
                    {omdbPercent}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
      {/if}

      <!-- ===============================
           TVmaze Integration
           =============================== -->
      {#if tvmazeEnabled}
      <div class="border border-border rounded-xl p-6 space-y-4">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h3 class="text-[13px] font-medium">TVmaze API</h3>
            <p class="text-[11px] text-text-tertiary mt-1">
              Free TV metadata for series and episodes (no API key required)
            </p>
          </div>
          <div class="flex items-center gap-2">
            <div class="relative" use:clickOutside={() => (showTvmazeHelp = false)}>
              <button
                type="button"
                class="h-8 w-8 rounded-full border border-border text-text-secondary hover:text-white hover:bg-bg-hover transition-all"
                on:click={toggleTvmazeHelp}
                aria-label="TVmaze integration info"
              >
                <Info class="h-4 w-4 mx-auto" />
              </button>
              {#if showTvmazeHelp}
                <div class="absolute right-0 mt-2 w-64 rounded-xl border border-border bg-bg-card p-4 text-[12px] text-text-secondary shadow-[0_12px_30px_rgba(0,0,0,0.35)] z-10">
                  <p class="text-[12px] text-text-primary font-medium mb-1">TVmaze quick start</p>
                  <p class="text-[11px] text-text-tertiary mb-3">No account needed. Toggle on to enable TV lookups.</p>
                  <ol class="space-y-1 text-[11px] text-text-secondary">
                    <li>Turn on the TVmaze integration</li>
                    <li>Pick TVmaze as a metadata source</li>
                    <li>Scan and enrich TV episodes</li>
                  </ol>
                </div>
              {/if}
            </div>
            <span
              class="px-2 py-1 text-[10px] font-medium text-text-secondary border border-border rounded-lg uppercase tracking-wide"
            >
              TV Series
            </span>
          </div>
        </div>

        <div class="flex items-center justify-between gap-4 rounded-lg border border-border bg-bg-card px-4 py-3">
          <div>
            <p class="text-[12px] font-medium text-text-primary">Enable TVmaze</p>
            <p class="text-[11px] text-text-tertiary">Use TVmaze for series + episode plots.</p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" class="sr-only peer" bind:checked={tvmazeEnabled} />
            <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
            <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
          </label>
        </div>

        {#if tvmazeUsage && tvmazeEnabled}
          <div class="pt-4 border-t border-border space-y-2">
            <div class="flex items-center justify-between text-[11px]">
              <span class="text-text-secondary uppercase tracking-wide">
                {usageLabel(tvmazeState)} · Usage (24h)
              </span>
              <span class="text-text-tertiary">
                Resets in {formatResetTime(tvmazeUsage.reset_time)}
              </span>
            </div>

            <div class="space-y-1.5">
              <div class="flex items-center justify-between text-[11px]">
                <span class="text-text-tertiary">
                  {tvmazeUsage.total_calls_24h} / {tvmazeUsage.limit} calls
                </span>
                <span class="text-text-tertiary">
                  {tvmazePercent}%
                </span>
              </div>

              <div
                class="relative h-3 bg-bg-primary rounded-full overflow-hidden"
              >
                <div
                  class="absolute inset-y-0 left-0 transition-all {usageBarColor(
                    tvmazeState,
                  )}"
                  style="width: {tvmazePercent}%"
                ></div>

                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-[10px] font-medium text-black/80">
                    {tvmazePercent}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
      {/if}

      <!-- ===============================
           TMDb Integration
           =============================== -->
      {#if tmdbEnabled}
      <div class="border border-border rounded-xl p-6 space-y-4">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h3 class="text-[13px] font-medium">TMDb API</h3>
            <p class="text-[11px] text-text-tertiary mt-1">
              The Movie Database - Comprehensive media database
            </p>
          </div>
          <div class="flex items-center gap-2">
            <div class="relative" use:clickOutside={() => (showTmdbHelp = false)}>
              <button
                type="button"
                class="h-8 w-8 rounded-full border border-border text-text-secondary hover:text-white hover:bg-bg-hover transition-all"
                on:click={toggleTmdbHelp}
                aria-label="How to get a TMDb API key"
              >
                <Info class="h-4 w-4 mx-auto" />
              </button>
              {#if showTmdbHelp}
                <div class="absolute right-0 mt-2 w-64 rounded-xl border border-border bg-bg-card p-4 text-[12px] text-text-secondary shadow-[0_12px_30px_rgba(0,0,0,0.35)] z-10">
                  <p class="text-[12px] text-text-primary font-medium mb-1">Get a TMDb API key</p>
                  <p class="text-[11px] text-text-tertiary mb-3">Requires a free TMDb account.</p>
                  <ol class="space-y-1 text-[11px] text-text-secondary">
                    <li>Sign in at <a class="text-white hover:underline" href="https://www.themoviedb.org" target="_blank" rel="noopener noreferrer">themoviedb.org</a></li>
                    <li>Go to Settings > API and request a key</li>
                    <li>Paste the key here and save</li>
                  </ol>
                </div>
              {/if}
            </div>
            <span
              class="px-2 py-1 text-[10px] font-medium text-text-secondary border border-border rounded-lg uppercase tracking-wide"
            >
              Movies & Series
            </span>
          </div>
        </div>

        <div class="flex items-center justify-between gap-4 rounded-lg border border-border bg-bg-card px-4 py-3">
          <div>
            <p class="text-[12px] font-medium text-text-primary">Enable TMDb</p>
            <p class="text-[11px] text-text-tertiary">Use TMDb for movies and TV metadata.</p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" class="sr-only peer" bind:checked={tmdbEnabled} />
            <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
            <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
          </label>
        </div>

        <div class="space-y-2">
          <label
            class="block text-[11px] font-medium text-text-secondary uppercase tracking-wide"
          >
            API Key
          </label>

          <input
            type="text"
            bind:value={tmdbApiKey}
            placeholder="Enter your TMDb API key"
            disabled={!tmdbEnabled}
            class="w-full px-4 py-3 bg-bg-card border border-border rounded-lg
                   text-[13px] placeholder:text-text-tertiary
                   focus:outline-none focus:border-white/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          />
        </div>

        {#if tmdbUsage && tmdbEnabled}
          <div class="pt-4 border-t border-border space-y-2">
            <div class="flex items-center justify-between text-[11px]">
              <span class="text-text-secondary uppercase tracking-wide">
                {usageLabel(tmdbState)} · Usage (24h)
              </span>
              <span class="text-text-tertiary">
                Resets in {formatResetTime(tmdbUsage.reset_time)}
              </span>
            </div>

            <div class="space-y-1.5">
              <div class="flex items-center justify-between text-[11px]">
                <span class="text-text-tertiary">
                  {tmdbUsage.total_calls_24h} / {tmdbUsage.limit} calls
                </span>
                <span class="text-text-tertiary">
                  {tmdbPercent}%
                </span>
              </div>

              <div
                class="relative h-3 bg-bg-primary rounded-full overflow-hidden"
              >
                <div
                  class="absolute inset-y-0 left-0 transition-all {usageBarColor(
                    tmdbState,
                  )}"
                  style="width: {tmdbPercent}%"
                ></div>

                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-[10px] font-medium text-black/80">
                    {tmdbPercent}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
      {/if}
    </div>
  </div>

  <button
    type="submit"
    disabled={saving}
    class="px-7 py-3.5 bg-white hover:bg-white/90 disabled:opacity-30 disabled:cursor-not-allowed
           text-black text-[13px] font-medium rounded-xl transition-all"
  >
    {saving ? "Saving…" : "Save Changes"}
  </button>
</form>
