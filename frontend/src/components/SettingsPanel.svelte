<script>
  import { onMount } from "svelte";
  import { getSettings, updateSettings } from "../lib/api.js";
  import { Skeleton } from "../lib/components/ui/skeleton";
  import GeneralSettings from "./settings/GeneralSettings.svelte";
  import IntegrationsSettings from "./settings/IntegrationsSettings.svelte";
  import FilenameCleaningSettings from "./settings/FilenameCleaningSettings.svelte";
  import FolderRulesSettings from "./settings/FolderRulesSettings.svelte";
  import TasksSettings from "./settings/TasksSettings.svelte";
  import { addToast } from "../lib/toastStore.js";
  import { Bolt, Calendar, Folder, Plug, Settings, Wand2 } from "lucide-svelte";

  let currentSection = "general";
  let settings = {};
  let loading = false;
  let saving = false;
  let error = null;
  let successMessage = null;

  const sections = [
    { id: "general",      label: "General",      icon: Settings },
    { id: "folder-rules", label: "Folder Rules",  icon: Folder },
    { id: "cleanup",      label: "Cleanup",        icon: Wand2 },
    { id: "integrations", label: "Integrations",   icon: Plug },
    { id: "tasks",        label: "Tasks",           icon: Bolt },
  ];

  onMount(async () => {
    await loadSettings();
  });

  async function loadSettings() {
    loading = true;
    error = null;
    const loadingStart = Date.now();

    try {
      settings = await getSettings();
    } catch (err) {
      error = `Failed to load settings: ${err.message}`;
    } finally {
      const elapsed = Date.now() - loadingStart;
      const minDelayMs = 500;
      if (elapsed < minDelayMs) {
        await new Promise((resolve) =>
          setTimeout(resolve, minDelayMs - elapsed),
        );
      }
      loading = false;
    }
  }

  async function handleSave(updates) {
    saving = true;
    error = null;
    successMessage = null;

    try {
      const result = await updateSettings(updates);
      successMessage = result.message || "Settings saved successfully";
      addToast({ message: successMessage, tone: "success" });

      // Reload settings
      await loadSettings();

      setTimeout(() => {
        successMessage = null;
      }, 3000);
    } catch (err) {
      error = `Failed to save settings: ${err.message}`;
      addToast({ message: error, tone: "error" });
    } finally {
      saving = false;
    }
  }
</script>

{#if loading}
  <div class="space-y-6">
    <div>
      <Skeleton className="h-6 w-32 mb-2" />
      <Skeleton className="h-4 w-64" />
    </div>
    <div class="flex gap-10">
      <div class="w-44 space-y-1.5">
        {#each Array(5) as _}
          <Skeleton className="h-9 w-full rounded-lg" />
        {/each}
      </div>
      <div class="flex-1 space-y-4">
        <div class="rounded-xl border border-border bg-card p-6 space-y-3">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
        <div class="rounded-xl border border-border bg-card p-6 space-y-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      </div>
    </div>
  </div>
{:else}
  <div class="space-y-8">
    <div>
      <h2 class="text-xl font-bold mb-1.5 text-text-primary">Settings</h2>
      <p class="text-[13px] text-text-secondary leading-relaxed">
        Configure metadata sources, cleanup rules, and scheduled scans.
      </p>
    </div>

    <div class="flex flex-col lg:flex-row gap-8 lg:gap-10">
      <!-- Sidebar Navigation -->
      <aside class="w-full lg:w-44 shrink-0">
        <nav class="space-y-0.5">
          {#each sections as section}
            {@const isActive = currentSection === section.id}
            <button
              class={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-[13px] font-medium transition-all duration-150 relative
                ${isActive
                  ? "bg-bg-hover text-text-primary"
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-hover/60"
                }`}
              on:click={() => (currentSection = section.id)}
            >
              {#if isActive}
                <span class="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-full bg-accent"></span>
              {/if}
              <svelte:component this={section.icon} class="w-4 h-4 shrink-0" />
              <span>{section.label}</span>
            </button>
          {/each}
        </nav>
      </aside>

      <!-- Main Content -->
      <div class="flex-1 min-w-0 space-y-4">
        {#if error}
          <div class="px-4 py-3 bg-red-500/8 border border-red-500/20 rounded-xl">
            <p class="text-[13px] text-red-300">{error}</p>
          </div>
        {/if}

        {#if successMessage}
          <div class="px-4 py-3 bg-emerald-500/8 border border-emerald-500/20 rounded-xl">
            <p class="text-[13px] text-emerald-300">{successMessage}</p>
          </div>
        {/if}

        <div class="rounded-xl border border-border bg-card shadow-[0_2px_8px_rgba(0,0,0,0.3),0_0_0_1px_rgba(255,255,255,0.04)] p-6 lg:p-8">
          {#if currentSection === "general"}
            <GeneralSettings {settings} {saving} onSave={handleSave} />
          {:else if currentSection === "folder-rules"}
            <FolderRulesSettings {settings} />
          {:else if currentSection === "scheduled"}
            <TasksSettings />
          {:else if currentSection === "cleanup"}
            <FilenameCleaningSettings {settings} {saving} onSave={handleSave} />
          {:else if currentSection === "integrations"}
            <IntegrationsSettings {settings} {saving} onSave={handleSave} />
          {:else if currentSection === "tasks"}
            <TasksSettings />
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}
