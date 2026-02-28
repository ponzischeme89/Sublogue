<script>
  import { onMount } from "svelte";
  import Footer from "./components/Footer.svelte";
  import AppSidebar from "./components/AppSidebar.svelte";
  import * as Sidebar from "./lib/components/ui/sidebar";
  import { Button } from "./lib/components/ui/button";
  import SettingsPanel from "./components/SettingsPanel.svelte";
  import ScanPanel from "./components/scan/ScanPanel.svelte";
  import HistoryPanel from "./components/HistoryPanel.svelte";
  import LibraryPanel from "./components/library/LibraryPanel.svelte";
  import AutomationList from "./routes/automation/AutomationList.svelte";
  import { Menu, AlertTriangle, AlertCircle } from "lucide-svelte";
  import ToastHost from "./components/ToastHost.svelte";
  import { healthCheck } from "./lib/api.js";
  import { currentTheme, themes } from "./lib/themeStore.js";

  let currentView = "scanner";
  let apiConfigured = false;
  let apiReachable = true;
  let apiErrorMessage = "";
  let selectedFiles = [];
  let metadataProvider = "omdb";
  let scanPanelKey = 0;
  let sidebarOpen = true;
  let sidebarCollapsed = false;
  let isMobile = false;

  // Apply theme on mount and when it changes
  function applyTheme(themeName) {
    const theme = themes[themeName];
    if (!theme) return;

    const root = document.documentElement;
    Object.entries(theme.colors).forEach(([key, value]) => {
      root.style.setProperty(`--${key}`, value);
    });

    if (themeName === "light") {
      root.classList.add("light-theme");
    } else {
      root.classList.remove("light-theme");
    }
  }

  function updateLayout() {
    isMobile = window.innerWidth < 768;
    if (isMobile) {
      sidebarOpen = false;
    } else {
      sidebarOpen = true;
    }
  }

  onMount(async () => {
    updateLayout();
    const onResize = () => updateLayout();
    window.addEventListener("resize", onResize);

    // Initialize theme
    applyTheme($currentTheme);

    try {
      const health = await healthCheck();
      apiConfigured = health.api_key_configured;
      apiReachable = true;
      apiErrorMessage = "";
    } catch (err) {
      console.error("Health check failed:", err);
      apiReachable = false;
      apiErrorMessage = "Backend unreachable. Start the server to use Sublogue.";
    }
    return () => {
      window.removeEventListener("resize", onResize);
    };
  });

  // Watch for theme changes
  $: if ($currentTheme) {
    applyTheme($currentTheme);
  }

  async function checkApiStatus() {
    try {
      const health = await healthCheck();
      apiConfigured = health.api_key_configured;
      apiReachable = true;
      apiErrorMessage = "";
    } catch (err) {
      console.error("Health check failed:", err);
      apiReachable = false;
      apiErrorMessage = "Backend unreachable. Start the server to use Sublogue.";
    }
  }

  async function navigateTo(view) {
    currentView = view;
    // Re-check API status when navigating to scanner (in case settings were just saved)
    if (view === "scanner") {
      await checkApiStatus();
    }
  }

  function handleProcessComplete() {
    scanPanelKey += 1;
  }

  function handleSidebarToggle() {
    if (isMobile) {
      sidebarOpen = !sidebarOpen;
    } else {
      sidebarCollapsed = !sidebarCollapsed;
    }
  }

  $: sidebarWidth = isMobile
    ? "15.5rem"
    : sidebarCollapsed
      ? "3.75rem"
      : "16rem";
</script>

<Sidebar.Provider
  style={`--sidebar-width: ${sidebarWidth}; --header-height: 4rem;`}
>
  {#if isMobile && sidebarOpen}
    <div
      class="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm"
      on:click={() => (sidebarOpen = false)}
      aria-hidden="true"
    ></div>
  {/if}
  <AppSidebar
    {currentView}
    onNavigate={navigateTo}
    onToggleSidebar={handleSidebarToggle}
    open={isMobile ? sidebarOpen : true}
    collapsed={!isMobile && sidebarCollapsed}
    {isMobile}
  />
  <Sidebar.Inset>
    <!-- Main Content -->
    <main class="flex-1 min-h-0">
      {#if isMobile && !sidebarOpen}
        <div class="px-4 pt-4">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            on:click={() => (sidebarOpen = true)}
            aria-label="Show sidebar"
          >
            <Menu class="h-3.5 w-3.5" />
            Menu
          </Button>
        </div>
      {/if}

      <!-- Status banners -->
      {#if !apiReachable}
        <div class="mx-4 sm:mx-6 md:mx-8 mt-4 flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/8 px-4 py-3">
          <AlertCircle class="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
          <p class="text-[13px] text-red-300 leading-relaxed">{apiErrorMessage}</p>
        </div>
      {:else if !apiConfigured && currentView === "scanner"}
        <div class="mx-4 sm:mx-6 md:mx-8 mt-4 flex items-start gap-3 rounded-xl border border-yellow-500/15 bg-yellow-500/6 px-4 py-3">
          <AlertTriangle class="h-4 w-4 text-yellow-400 mt-0.5 shrink-0" />
          <p class="text-[13px] text-yellow-200/80 leading-relaxed">
            Configure a metadata source in Settings &rsaquo; Integrations to get started
          </p>
        </div>
      {/if}

      <div class="px-4 sm:px-6 md:px-8 py-7 sm:py-9 md:py-10">
        {#if currentView === "settings"}
          <SettingsPanel />
        {:else if currentView === "history"}
          <HistoryPanel />
        {:else if currentView === "scanner"}
          {#key scanPanelKey}
            <ScanPanel
              bind:selectedFilePaths={selectedFiles}
              bind:metadataProvider
              {apiConfigured}
              onOpenSettings={() => navigateTo("settings")}
              onOpenHistory={() => navigateTo("history")}
            />
          {/key}
        {:else if currentView === "library"}
          <LibraryPanel />
        {:else if currentView === "automation"}
          <AutomationList />
        {/if}
      </div>
    </main>

    <Footer />
  </Sidebar.Inset>
  <ToastHost />
</Sidebar.Provider>
