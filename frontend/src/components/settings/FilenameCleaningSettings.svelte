<script>
  import { AlertTriangle, ArrowRight } from "lucide-svelte";

  export let settings = {};
  export let saving = false;
  export let onSave;

  let stripKeywords = settings.strip_keywords !== false;
  let cleanSubtitleContent = settings.clean_subtitle_content !== false;
  let forceRemoveKeywords = Array.isArray(settings.clean_subtitle_force_remove)
    ? settings.clean_subtitle_force_remove.join(", ")
    : settings.clean_subtitle_force_remove || "YTS, OpenSubtitles";

  // Example filenames to demonstrate the cleaning
  const filenameExamples = [
    { before: "Movie.2024.1080p.BluRay.x264-YTS", after: "Movie (2024)" },
    {
      before: "The.Matrix.1999.REMASTERED.2160p.UHD",
      after: "The Matrix (1999)",
    },
    { before: "Inception.2010.HDRip.XviD-RARBG", after: "Inception (2010)" },
  ];

  // Example subtitle content cleaning
  const contentExamples = [
    { before: "Hello there. www.YTS.mx", after: "Hello there." },
    { before: "Subtitles by OpenSubtitles", after: "(removed)" },
    { before: "Downloaded from RARBG", after: "(removed)" },
  ];

  // Keywords that get stripped from filenames
  const filenameKeywords = [
    { name: "Quality", examples: ["480p", "720p", "1080p", "4K", "HDR"] },
    { name: "Source", examples: ["BluRay", "WEBRip", "DVDRip", "HDTV"] },
    { name: "Codecs", examples: ["x264", "x265", "HEVC", "AAC", "DTS"] },
    { name: "Groups", examples: ["YTS", "RARBG", "EZTV", "PSA"] },
  ];

  // Keywords removed from subtitle content
  const contentKeywords = [
    {
      name: "Sites",
      examples: ["YTS.mx", "RARBG", "OpenSubtitles", "Subscene"],
    },
    {
      name: "Watermarks",
      examples: ["Subtitles by", "Synced by", "Downloaded from"],
    },
    {
      name: "Promo",
      examples: ["Support us", "Get more subtitles", "Visit us at"],
    },
  ];

  function handleSubmit() {
    onSave({
      strip_keywords: stripKeywords,
      clean_subtitle_content: cleanSubtitleContent,
      clean_subtitle_force_remove: forceRemoveKeywords
        .split(/[\n,]+/)
        .map((entry) => entry.trim())
        .filter(Boolean),
    });
  }
</script>

<form on:submit|preventDefault={handleSubmit} class="space-y-10">
  <!-- Section 1: Filename Cleaning -->
  <div>
    <h2 class="text-lg font-semibold text-text-primary">Filename Cleaning</h2>
    <p class="text-[13px] text-text-secondary mb-6">
      Clean up movie filenames before searching for metadata.
    </p>

    <!-- Toggle -->
    <div class="p-5 bg-bg-secondary border border-border rounded-xl mb-5">
      <label class="flex items-start justify-between gap-4 rounded-xl border border-border bg-bg-secondary/40 px-4 py-3">
        <div class="flex-1">
          <div class="text-[14px] font-medium mb-1">
            Strip Filename Keywords
          </div>
          <div class="text-[12px] text-text-tertiary leading-relaxed">
            Remove quality indicators (1080p, BluRay), codecs (x264, HEVC), and
            release group names from filenames before looking up movie
            information.
          </div>
        </div>
        <span class="relative mt-0.5 inline-flex items-center">
          <input type="checkbox" bind:checked={stripKeywords} class="sr-only peer" />
          <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
          <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
        </span>
      </label>
    </div>

    <!-- Collapsible Details -->
    {#if stripKeywords}
      <div class="space-y-4 pl-2 border-l-2 border-border ml-2">
        <!-- Example Transformations -->
        <div class="bg-bg-card border border-border rounded-xl overflow-hidden">
          <div class="px-4 py-2.5 border-b border-border bg-bg-secondary">
            <span
              class="text-[11px] font-medium text-text-secondary uppercase tracking-wide"
              >Examples</span
            >
          </div>
          <div class="divide-y divide-border">
            {#each filenameExamples as example}
              <div class="px-4 py-2.5 flex items-center gap-3">
                <div class="flex-1 min-w-0">
                  <code class="text-[11px] text-text-tertiary break-all"
                    >{example.before}</code
                  >
                </div>
                <ArrowRight class="w-3.5 h-3.5 text-text-tertiary flex-shrink-0" />
                <div class="flex-shrink-0">
                  <code class="text-[11px] text-green-400 font-medium"
                    >{example.after}</code
                  >
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Keywords List -->
        <div class="bg-bg-card border border-border rounded-xl p-4">
          <div class="flex flex-wrap gap-x-6 gap-y-2">
            {#each filenameKeywords as category}
              <div>
                <span
                  class="text-[10px] font-medium text-text-secondary uppercase"
                  >{category.name}:</span
                >
                <span class="text-[11px] text-text-tertiary ml-1.5"
                  >{category.examples.join(", ")}</span
                >
              </div>
            {/each}
          </div>
        </div>
      </div>
    {/if}
  </div>

  <!-- Section 2: Subtitle Content Cleaning -->
  <div>
    <h2 class="text-lg font-semibold text-text-primary">Subtitle Content Cleaning</h2>
    <p class="text-[13px] text-text-secondary mb-6">
      Remove embedded ads and watermarks from inside subtitle text.
    </p>

    <!-- Toggle -->
    <div class="p-5 bg-bg-secondary border border-border rounded-xl mb-5">
      <label class="flex items-start justify-between gap-4 rounded-xl border border-border bg-bg-secondary/40 px-4 py-3">
        <div class="flex-1">
          <div class="text-[14px] font-medium mb-1">Remove Subtitle Ads</div>
          <div class="text-[12px] text-text-tertiary leading-relaxed">
            Automatically remove release group watermarks (YTS, RARBG), subtitle
            site ads (OpenSubtitles), and promotional text embedded in the
            actual subtitle dialogue.
          </div>
        </div>
        <span class="relative mt-0.5 inline-flex items-center">
          <input type="checkbox" bind:checked={cleanSubtitleContent} class="sr-only peer" />
          <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
          <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
        </span>
      </label>
    </div>

    <!-- Collapsible Details -->
    {#if cleanSubtitleContent}
      <div class="space-y-4 pl-2 border-l-2 border-border ml-2">
        <div class="bg-bg-card border border-border rounded-xl p-4 space-y-3">
          <div class="text-[11px] text-text-tertiary uppercase tracking-wide">
            Force Remove Keywords
          </div>
          <textarea
            rows="3"
            bind:value={forceRemoveKeywords}
            class="w-full resize-none rounded-lg border border-white/10 bg-bg-primary/60 px-3 py-2 text-[12px] text-text-secondary placeholder:text-text-tertiary focus:border-accent focus:outline-none"
            placeholder="YTS, OpenSubtitles"
          ></textarea>
          <p class="text-[11px] text-text-tertiary">
            Any subtitle block containing one of these strings (partial match)
            is removed entirely. Separate values with commas or new lines.
          </p>
        </div>

        <!-- Example Transformations -->
        <div class="bg-bg-card border border-border rounded-xl overflow-hidden">
          <div class="px-4 py-2.5 border-b border-border bg-bg-secondary">
            <span
              class="text-[11px] font-medium text-text-secondary uppercase tracking-wide"
              >Examples</span
            >
          </div>
          <div class="divide-y divide-border">
            {#each contentExamples as example}
              <div class="px-4 py-2.5 flex items-center gap-3">
                <div class="flex-1 min-w-0">
                  <code class="text-[11px] text-text-tertiary break-all"
                    >{example.before}</code
                  >
                </div>
                <ArrowRight class="w-3.5 h-3.5 text-text-tertiary flex-shrink-0" />
                <div class="flex-shrink-0">
                  <code
                    class="text-[11px] {example.after === '(removed)'
                      ? 'text-red-400'
                      : 'text-green-400'} font-medium">{example.after}</code
                  >
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Keywords List -->
        <div class="bg-bg-card border border-border rounded-xl p-4">
          <div class="flex flex-wrap gap-x-6 gap-y-2">
            {#each contentKeywords as category}
              <div>
                <span
                  class="text-[10px] font-medium text-text-secondary uppercase"
                  >{category.name}:</span
                >
                <span class="text-[11px] text-text-tertiary ml-1.5"
                  >{category.examples.join(", ")}</span
                >
              </div>
            {/each}
          </div>
        </div>

        <!-- Note about timing -->
        <div
          class="flex items-start gap-3 p-4 bg-amber-500/5 border border-amber-500/20 rounded-xl"
        >
          <AlertTriangle class="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <div class="text-[12px] font-medium text-amber-300 mb-1">
              Modifies subtitle content
            </div>
            <div class="text-[11px] text-amber-300/70 leading-relaxed">
              This setting will modify the actual text inside your subtitle file
              to remove ads. Subtitle timing is never changed - only ad text is
              removed or entire ad blocks are deleted.
            </div>
          </div>
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
    {saving ? "Saving..." : "Save Changes"}
  </button>
</form>
