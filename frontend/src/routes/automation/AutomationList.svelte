<script>
  import { onMount } from "svelte";
  import {
    getAutomationRules,
    createAutomationRule,
    updateAutomationRule,
    deleteAutomationRule,
    runAutomationRule,
  } from "../../lib/api.js";
  import { Button } from "../../lib/components/ui/button";
  import { Skeleton } from "../../lib/components/ui/skeleton";
  import AutomationForm from "./AutomationForm.svelte";
  import { addToast } from "../../lib/toastStore.js";
  import { Play, RefreshCcw, Trash2, Edit3, Wand2 } from "lucide-svelte";

  let rules = [];
  let loading = false;
  let saving = false;
  let error = null;
  let editingRule = null;
  let showForm = false;
  let dryRunByRule = {};
  let running = {};

  async function loadRules() {
    loading = true;
    error = null;
    try {
      const response = await getAutomationRules();
      rules = response.rules || [];
    } catch (err) {
      error = `Failed to load automation rules: ${err.message}`;
    } finally {
      loading = false;
    }
  }

  onMount(loadRules);

  function openCreate() {
    editingRule = null;
    showForm = true;
  }

  function openEdit(rule) {
    editingRule = rule;
    showForm = true;
  }

  function closeForm() {
    showForm = false;
    editingRule = null;
  }

  async function handleSave(rule) {
    saving = true;
    try {
      if (editingRule) {
        await updateAutomationRule(editingRule.id, rule);
        addToast({ message: "Automation rule updated.", tone: "success" });
      } else {
        await createAutomationRule(rule);
        addToast({ message: "Automation rule created.", tone: "success" });
      }
      await loadRules();
      closeForm();
    } catch (err) {
      addToast({
        message: `Failed to save rule: ${err.message}`,
        tone: "error",
      });
    } finally {
      saving = false;
    }
  }

  async function toggleEnabled(rule) {
    try {
      await updateAutomationRule(rule.id, { enabled: !rule.enabled });
      await loadRules();
    } catch (err) {
      addToast({
        message: `Failed to update rule: ${err.message}`,
        tone: "error",
      });
    }
  }

  async function removeRule(rule) {
    if (!confirm(`Delete rule "${rule.name}"?`)) return;
    try {
      await deleteAutomationRule(rule.id);
      addToast({ message: "Automation rule deleted.", tone: "success" });
      await loadRules();
    } catch (err) {
      addToast({
        message: `Failed to delete rule: ${err.message}`,
        tone: "error",
      });
    }
  }

  async function runRule(rule) {
    running[rule.id] = true;
    running = { ...running };
    try {
      const result = await runAutomationRule(
        rule.id,
        dryRunByRule[rule.id] === true,
      );
      const label = result.dry_run ? "Dry run" : "Run";
      addToast({
        message: `${label} complete. ${result.files_modified}/${result.files_scanned} modified.`,
        tone: "success",
      });
    } catch (err) {
      addToast({
        message: `Run failed: ${err.message}`,
        tone: "error",
      });
    } finally {
      running[rule.id] = false;
      running = { ...running };
    }
  }
</script>

<div class="space-y-8">
  <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <div>
      <h2 class="text-xl font-bold text-text-primary">Automations</h2>
      <p class="text-[13px] text-text-secondary">
        Schedule cleanups that run on cron-style timings. Each rule scans the
        selected folders and removes lines matching your patterns.
      </p>
    </div>
    <div class="flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        className="border-white/15 text-text-secondary hover:bg-white/10"
        on:click={loadRules}
      >
        <RefreshCcw class="h-4 w-4" />
        Refresh
      </Button>
      <Button size="sm" className="bg-white text-black hover:bg-white/90" on:click={openCreate}>
        <Wand2 class="h-4 w-4" />
        New rule
      </Button>
    </div>
  </div>

  {#if showForm}
    <div class="rounded-2xl border border-border bg-card/60 p-6">
      <AutomationForm
        rule={editingRule}
        saving={saving}
        onSave={handleSave}
        onCancel={closeForm}
      />
    </div>
  {/if}

  {#if error}
    <div class="rounded-xl border border-red-500/20 bg-red-500/5 px-5 py-4">
      <p class="text-[13px] text-red-300">{error}</p>
    </div>
  {/if}

  {#if loading}
    <div class="space-y-3">
      {#each Array(3) as _}
        <div class="rounded-2xl border border-border bg-card/60 p-6">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="mt-3 h-3 w-56" />
          <Skeleton className="mt-4 h-10 w-full" />
        </div>
      {/each}
    </div>
  {:else if rules.length === 0}
    <div class="rounded-2xl border border-border bg-card/60 p-12 text-center">
      <p class="text-[13px] text-text-secondary">No automation rules yet.</p>
      <p class="text-[11px] text-text-tertiary mt-2">
        Create one to automatically clean subtitle files.
      </p>
    </div>
  {:else}
    <div class="space-y-4">
      {#each rules as rule}
        <div class="rounded-2xl border border-border bg-card/60 p-6 space-y-4">
          <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div class="space-y-1">
              <div class="text-[14px] font-semibold text-text-primary">
                {rule.name}
              </div>
              <div class="text-[12px] text-text-tertiary">
                Schedule: <span class="font-mono">{rule.schedule}</span>
              </div>
              <div class="text-[12px] text-text-tertiary">
                Targets: {rule.target_folders.length} folder
                {rule.target_folders.length === 1 ? "" : "s"}
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="border-white/15 text-text-secondary hover:bg-white/10"
                on:click={() => openEdit(rule)}
              >
                <Edit3 class="h-4 w-4" />
                Edit
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="border-white/15 text-text-secondary hover:bg-white/10"
                on:click={() => removeRule(rule)}
              >
                <Trash2 class="h-4 w-4" />
                Delete
              </Button>
            </div>
          </div>

          <div class="rounded-xl border border-border bg-bg-secondary/40 p-4 space-y-3">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <label class="flex items-center gap-2 text-[12px] text-text-secondary">
                <input
                  type="checkbox"
                  checked={rule.enabled}
                  on:change={() => toggleEnabled(rule)}
                  class="h-4 w-4"
                />
                Enabled
              </label>

              <label class="flex items-center gap-2 text-[12px] text-text-secondary">
                <input
                  type="checkbox"
                  bind:checked={dryRunByRule[rule.id]}
                  class="h-4 w-4"
                />
                Dry run
              </label>
            </div>

            <div class="flex flex-wrap items-center gap-2 text-[11px] text-text-tertiary">
              {#each rule.patterns as pattern}
                <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                  {pattern}
                </span>
              {/each}
            </div>

            <div class="flex flex-wrap items-center gap-2 text-[11px] text-text-tertiary">
              {#each rule.target_folders as folder}
                <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono">
                  {folder}
                </span>
              {/each}
            </div>

            <Button
              size="sm"
              className="bg-white text-black hover:bg-white/90"
              on:click={() => runRule(rule)}
              disabled={running[rule.id]}
            >
              <Play class="h-4 w-4" />
              {running[rule.id] ? "Running..." : "Run now"}
            </Button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
