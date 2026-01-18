<script>
  import { onMount } from "svelte";
  import { getLibraryReport } from "../lib/api.js";
  import { Button } from "../lib/components/ui/button";
  import { ChevronDown, ChevronUp, RefreshCcw, FileText } from "lucide-svelte";

  let items = [];
  let loading = false;
  let error = null;
  let expanded = {};

  async function loadLibrary() {
    loading = true;
    error = null;
    try {
      const response = await getLibraryReport();
      items = response.items || [];
    } catch (err) {
      error = `Failed to load library report: ${err.message}`;
    } finally {
      loading = false;
    }
  }

  function toggleScan(key) {
    expanded = { ...expanded, [key]: !expanded[key] };
  }

  onMount(loadLibrary);
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <h2 class="text-xl font-bold text-text-primary">Library Health</h2>
      <p class="text-[13px] text-text-secondary">
        Review subtitles from each scan and spot missing plots, duplicates, and insufficient gaps.
      </p>
    </div>
    <Button
      variant="outline"
      size="sm"
      className="border-white/15 text-text-secondary hover:bg-white/10"
      on:click={loadLibrary}
      disabled={loading}
    >
      <RefreshCcw class="h-4 w-4" />
      Refresh
    </Button>
  </div>

  {#if error}
    <div class="px-5 py-4 bg-red-500/5 border border-red-500/20 rounded-xl">
      <p class="text-[13px] text-red-300">{error}</p>
    </div>
  {/if}

  {#if loading}
    <div class="text-[13px] text-text-secondary">Loading library report...</div>
  {:else if items.length === 0}
    <div class="border border-border rounded-2xl p-12 text-center">
      <div class="flex flex-col items-center gap-4">
        <FileText class="w-12 h-12 text-text-tertiary" />
        <div>
          <p class="text-[13px] text-text-secondary mb-1">No scan data yet</p>
          <p class="text-[11px] text-text-tertiary">Run a scan to populate the library report.</p>
        </div>
      </div>
    </div>
  {:else}
    <div class="space-y-4">
      {#each items as item}
        <div class="rounded-2xl border border-border bg-card/60 overflow-hidden">
          <div class="px-6 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div class="space-y-1">
              <div class="text-[13px] font-semibold text-text-primary">
                {item.title}{item.year ? ` (${item.year})` : ""}
              </div>
              <div class="text-[11px] text-text-tertiary">
                {item.files.length} subtitle file{item.files.length === 1 ? "" : "s"}
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-[11px] text-yellow-200 bg-yellow-500/10 border border-yellow-500/30 px-3 py-1 rounded-full">
                Missing: {item.health.missing_plot}
              </span>
              <span class="text-[11px] text-orange-200 bg-orange-500/10 border border-orange-500/30 px-3 py-1 rounded-full">
                Duplicates: {item.health.duplicate_plot}
              </span>
              <span class="text-[11px] text-red-200 bg-red-500/10 border border-red-500/30 px-3 py-1 rounded-full">
                Gap issues: {item.health.insufficient_gap}
              </span>
              <button
                class="ml-2 text-text-secondary hover:text-white transition-colors"
                on:click={() => toggleScan(item.title)}
                aria-label="Toggle scan details"
              >
                {#if expanded[item.title]}
                  <ChevronUp class="h-4 w-4" />
                {:else}
                  <ChevronDown class="h-4 w-4" />
                {/if}
              </button>
            </div>
          </div>

          {#if expanded[item.title]}
            <div class="border-t border-border bg-bg-secondary/40">
              <div class="px-6 py-4 overflow-x-auto">
                <table class="min-w-full text-[12px] text-text-secondary">
                  <thead>
                    <tr class="text-text-tertiary text-[11px] uppercase tracking-wide">
                      <th class="text-left py-2 pr-4">File</th>
                      <th class="text-left py-2 pr-4">Status</th>
                      <th class="text-left py-2 pr-4">Plot</th>
                      <th class="text-left py-2">Issues</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-border">
                    {#each item.files as file}
                      <tr>
                        <td class="py-3 pr-4 text-text-primary">
                          {file.display_name || file.name}
                        </td>
                        <td class="py-3 pr-4">{file.status || "Not Loaded"}</td>
                        <td class="py-3 pr-4">
                          {file.has_plot ? "Present" : "Missing"}
                        </td>
                        <td class="py-3">
                          {#if file.issues.length === 0}
                            <span class="text-green-300">Healthy</span>
                          {:else}
                            <div class="space-y-1">
                              {#each file.issues as issue}
                                <div class="text-[11px] text-red-200">
                                  {issue.type.replace("_", " ")} — {issue.reason}
                                </div>
                              {/each}
                            </div>
                          {/if}
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
