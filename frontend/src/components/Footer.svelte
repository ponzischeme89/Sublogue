<script>
  import { fade } from "svelte/transition";
  import { onMount, onDestroy } from "svelte";

  // ----------------------------------------
  // Quote rotation config
  // ----------------------------------------
  const ROTATE_MS = 6000;

  const quotes = [
    "Because subtitles deserve a prologue too.",
    "Turning subtitles into storytellers.",
    "Your film had a plot. Your subtitles should know it.",
    "For people who read movies more than watch them.",
    "Subtitles, but make them literary.",
    "Every story deserves context — even at 24fps.",
    "A little plot. Zero desync. Absolute peace.",
    "Metadata for humans who actually notice.",
    "Because ‘Hello sir’ should never be late.",
    "Subtitles with opinions. Quiet ones.",
    "Built for people who pause movies to read properly.",
    "Context is the difference between noise and meaning.",
    "Respect the subtitles. Respect yourself.",
  ];

  let quoteIndex = Math.floor(Math.random() * quotes.length);
  let interval;

  function nextQuote() {
    quoteIndex = (quoteIndex + 1) % quotes.length;
  }

  onMount(() => {
    interval = setInterval(nextQuote, ROTATE_MS);
  });

  onDestroy(() => {
    clearInterval(interval);
  });
</script>

<footer class="border-t border-border bg-bg-primary">
  <div class="max-w-7xl mx-auto px-6 md:px-8 py-10">
    <div class="flex flex-col gap-6 text-[11px] text-text-tertiary">
      <!-- Quote -->
      <div class="min-h-[1.2em] text-center sm:text-left">
        {#key quoteIndex}
          <span
            class="italic text-text-secondary/80 tracking-wide"
            transition:fade={{ duration: 350 }}
          >
            “{quotes[quoteIndex]}”
          </span>
        {/key}
      </div>

      <!-- Footer bar -->
      <div
        class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        <!-- Left -->
        <div class="flex items-center gap-3 text-[11px]">
          <span class="hidden sm:inline opacity-30">•</span>
          <span class="text-text-secondary"> Open source (AGPL-3.0) </span>
          <span class="hidden sm:inline opacity-30">•</span>
          <span class="text-text-tertiary"> Made in NZ 🇳🇿 </span>
        </div>

        <!-- Right -->
        <div class="flex items-center gap-6">
          <span class="flex items-center gap-2">
            <a
              href="https://github.com/ponzischeme89/Sublogue"
              target="_blank"
              rel="noopener noreferrer"
              class="text-text-secondary hover:text-text-primary transition-colors underline-offset-4 hover:underline"
            >
              Github
            </a>
          </span>
        </div>
      </div>
    </div>
  </div>
</footer>
