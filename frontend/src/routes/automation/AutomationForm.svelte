<script>
  import { Button } from "../../lib/components/ui/button";

  export let rule = null;
  export let saving = false;
  export let onSave;
  export let onCancel;

  let name = rule?.name || "";
  let schedule = rule?.schedule || "0 3 * * SUN";
  let enabled = rule?.enabled ?? true;
  let patterns = rule?.patterns ? [...rule.patterns] : ["YTS", "YIFY"];
  let targetFolders = rule?.target_folders
    ? [...rule.target_folders]
    : ["/media/movies"];

  $: if (rule) {
    name = rule.name || "";
    schedule = rule.schedule || "0 3 * * SUN";
    enabled = rule.enabled ?? true;
    patterns = rule.patterns ? [...rule.patterns] : [];
    targetFolders = rule.target_folders ? [...rule.target_folders] : [];
  }

  function addPattern() {
    patterns = [...patterns, ""];
  }

  function updatePattern(index, value) {
    patterns[index] = value;
    patterns = [...patterns];
  }

  function removePattern(index) {
    patterns = patterns.filter((_, idx) => idx !== index);
  }

  function addFolder() {
    targetFolders = [...targetFolders, ""];
  }

  function updateFolder(index, value) {
    targetFolders[index] = value;
    targetFolders = [...targetFolders];
  }

  function removeFolder(index) {
    targetFolders = targetFolders.filter((_, idx) => idx !== index);
  }

  function handleSubmit() {
    const cleanPatterns = patterns.map((p) => p.trim()).filter(Boolean);
    const cleanFolders = targetFolders.map((f) => f.trim()).filter(Boolean);

    onSave({
      name: name.trim(),
      schedule: schedule.trim(),
      enabled,
      patterns: cleanPatterns,
      target_folders: cleanFolders,
    });
  }
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h3 class="text-[15px] font-semibold text-text-primary">
        {rule ? "Edit automation rule" : "Create automation rule"}
      </h3>
      <p class="text-[12px] text-text-tertiary">
        Automations run on a cron schedule and process every .srt file in the
        selected folders.
      </p>
    </div>
    <span
      class="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-wide text-text-tertiary"
    >
      Cron
    </span>
  </div>

  <div class="grid gap-4 md:grid-cols-2">
    <div class="space-y-2">
      <label class="block text-[11px] uppercase tracking-wide text-text-tertiary">
        Rule name
      </label>
      <input
        type="text"
        bind:value={name}
        placeholder="Clean YTS/YIFY lines"
        class="w-full rounded-lg border border-border bg-bg-card px-4 py-3 text-[13px] focus:outline-none focus:border-white/30"
      />
    </div>
    <div class="space-y-2">
      <label class="block text-[11px] uppercase tracking-wide text-text-tertiary">
        Schedule
      </label>
      <input
        type="text"
        bind:value={schedule}
        placeholder="0 3 * * SUN"
        class="w-full rounded-lg border border-border bg-bg-card px-4 py-3 text-[13px] font-mono focus:outline-none focus:border-white/30"
      />
      <p class="text-[11px] text-text-tertiary">
        Example: <span class="font-mono">0 3 * * SUN</span> runs Sundays at 3am.
      </p>
    </div>
  </div>

  <label class="flex items-center justify-between gap-4 rounded-xl border border-border bg-bg-secondary/40 px-4 py-3">
    <div>
      <div class="text-[13px] font-medium">Enabled</div>
      <div class="text-[11px] text-text-tertiary">
        Disabled rules are saved but do not run.
      </div>
    </div>
    <span class="relative inline-flex items-center">
      <input type="checkbox" bind:checked={enabled} class="sr-only peer" />
      <span class="h-6 w-11 rounded-full border border-border bg-bg-card transition-colors peer-checked:bg-accent peer-checked:border-accent/60"></span>
      <span class="absolute left-0.5 h-5 w-5 rounded-full bg-text-tertiary transition-transform peer-checked:translate-x-5 peer-checked:bg-bg-primary"></span>
    </span>
  </label>

  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-[12px] font-medium text-text-primary">Patterns</p>
        <p class="text-[11px] text-text-tertiary">Lines containing these values are removed.</p>
      </div>
      <Button
        variant="outline"
        size="sm"
        className="border-white/15 text-text-secondary hover:bg-white/10"
        on:click={addPattern}
      >
        Add
      </Button>
    </div>

    <div class="space-y-2">
      {#each patterns as pattern, index}
        <div class="flex items-center gap-2">
          <input
            type="text"
            value={pattern}
            on:input={(e) => updatePattern(index, e.target.value)}
            placeholder="YTS"
            class="flex-1 rounded-lg border border-border bg-bg-card px-4 py-2 text-[13px] focus:outline-none focus:border-white/30"
          />
          <Button
            variant="outline"
            size="sm"
            className="border-white/15 text-text-secondary hover:bg-white/10"
            on:click={() => removePattern(index)}
          >
            Remove
          </Button>
        </div>
      {/each}
    </div>
  </div>

  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-[12px] font-medium text-text-primary">Target folders</p>
        <p class="text-[11px] text-text-tertiary">All .srt files under these paths are scanned.</p>
      </div>
      <Button
        variant="outline"
        size="sm"
        className="border-white/15 text-text-secondary hover:bg-white/10"
        on:click={addFolder}
      >
        Add
      </Button>
    </div>

    <div class="space-y-2">
      {#each targetFolders as folder, index}
        <div class="flex items-center gap-2">
          <input
            type="text"
            value={folder}
            on:input={(e) => updateFolder(index, e.target.value)}
            placeholder="/media/movies"
            class="flex-1 rounded-lg border border-border bg-bg-card px-4 py-2 text-[13px] font-mono focus:outline-none focus:border-white/30"
          />
          <Button
            variant="outline"
            size="sm"
            className="border-white/15 text-text-secondary hover:bg-white/10"
            on:click={() => removeFolder(index)}
          >
            Remove
          </Button>
        </div>
      {/each}
    </div>
  </div>

  <div class="flex flex-col gap-3 sm:flex-row sm:justify-end">
    <Button
      variant="outline"
      size="sm"
      className="border-white/15 text-text-secondary hover:bg-white/10"
      on:click={() => onCancel && onCancel()}
    >
      Cancel
    </Button>
    <Button
      size="sm"
      className="bg-white text-black hover:bg-white/90"
      on:click={handleSubmit}
      disabled={saving}
    >
      {saving ? "Saving..." : "Save Rule"}
    </Button>
  </div>
</div>
