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
    { id: "general", label: "General", icon: "settings" },
    { id: "folder-rules", label: "Folder Rules", icon: "folder" },
    { id: "cleanup", label: "Cleanup", icon: "wand" },
    { id: "integrations", label: "Integrations", icon: "plug" },
    { id: "tasks", label: "Tasks", icon: "bolt" },
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
    <div class="flex gap-12">
      <div class="w-48 space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
      <div class="flex-1 space-y-4">
        <div class="rounded-lg border border-border bg-card p-6 space-y-3">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
        <div class="rounded-lg border border-border bg-card p-6 space-y-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
        <div class="rounded-lg border border-border bg-card p-6 space-y-3">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      </div>
    </div>
  </div>
{:else}
  <div class="space-y-8">
    <div>
      <h2 class="text-xl font-bold mb-2 text-text-primary">Settings</h2>
      <p class="text-[13px] text-text-secondary leading-relaxed">
        Configure metadata sources, cleanup rules, and scheduled scans.
      </p>
    </div>

    <div class="flex flex-col lg:flex-row gap-8 lg:gap-12">
      <!-- Sidebar Navigation -->
      <aside class="w-full lg:w-48 flex-shrink-0">
        <nav class="space-y-0.5">
          {#each sections as section}
            <button
              class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-all border
                   {currentSection === section.id
                ? 'bg-white text-black border-white'
                : 'text-text-secondary hover:text-white hover:bg-bg-hover border-transparent'}"
              on:click={() => (currentSection = section.id)}
            >
              {#if section.icon === "settings"}
                <Settings class="w-4 h-4" />
              {:else if section.icon === "calendar"}
                <Calendar class="w-4 h-4" />
              {:else if section.icon === "bolt"}
                <Bolt class="w-4 h-4" />
              {:else if section.icon === "wand"}
                <Wand2 class="w-4 h-4" />
              {:else if section.icon === "plug"}
                <Plug class="w-4 h-4" />
              {:else if section.icon === "folder"}
                <Folder class="w-4 h-4" />
              {/if}
              <span class="text-[13px] font-medium">{section.label}</span>
            </button>
          {/each}
        </nav>
      </aside>

      <!-- Main Content -->
      <div class="flex-1 min-w-0">
        {#if error}
          <div
            class="mb-6 px-5 py-4 bg-red-500/5 border border-red-500/20 rounded-xl"
          >
            <p class="text-[13px] text-red-300">{error}</p>
          </div>
        {/if}

        {#if successMessage}
          <div
            class="mb-6 px-5 py-4 bg-green-500/5 border border-green-500/20 rounded-xl"
          >
            <p class="text-[13px] text-green-300">{successMessage}</p>
          </div>
        {/if}

        <div
          class="rounded-xl border border-border bg-card/60 p-6 lg:p-8 shadow-sm"
        >
          {#if currentSection === "general"}
            <GeneralSettings {settings} {saving} onSave={handleSave} />
          {:else if currentSection === "folder-rules"}
            <FolderRulesSettings {settings} />
          {:else if currentSection === "scheduled"}
            <ScheduledScansSettings {settings} />
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
