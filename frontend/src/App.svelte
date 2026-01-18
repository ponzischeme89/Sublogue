<script>
  import { onMount } from "svelte";
  import Footer from "./components/Footer.svelte";
  import AppSidebar from "./components/AppSidebar.svelte";
  import * as Sidebar from "./lib/components/ui/sidebar";
  import { Button } from "./lib/components/ui/button";
  import SettingsPanel from "./components/SettingsPanel.svelte";
  import ScanPanel from "./components/ScanPanel.svelte";
  import HistoryPanel from "./components/HistoryPanel.svelte";
  import LibraryPanel from "./components/LibraryPanel.svelte";
  import { Menu } from "lucide-svelte";
  import ToastHost from "./components/ToastHost.svelte";
  import { healthCheck } from "./lib/api.js";
  import { currentTheme, themes } from "./lib/themeStore.js";

  let currentView = "scanner";
  let apiConfigured = false;
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
    } catch (err) {
      console.error("Health check failed:", err);
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
    } catch (err) {
      console.error("Health check failed:", err);
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
      class="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm"
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
    <main class="flex-1">
      {#if isMobile && !sidebarOpen}
        <div class="px-4 sm:px-6 md:px-8 pt-4">
          <Button
            variant="outline"
            size="sm"
            className="border-white/15 text-text-secondary hover:bg-white/10"
            on:click={() => (sidebarOpen = true)}
            aria-label="Show sidebar"
          >
            <Menu class="h-4 w-4" />
            Menu
          </Button>
        </div>
      {/if}
      {#if !apiConfigured && currentView === "scanner"}
        <div class="border-b border-yellow-500/10 bg-yellow-500/5">
          <div class="px-6 md:px-8 py-3">
            <p class="text-[13px] text-yellow-100">
              Configure a metadata source in Settings to get started
            </p>
          </div>
        </div>
      {/if}

      <div class="px-4 sm:px-6 md:px-8 py-6 sm:py-8 md:py-10">
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
        {/if}
      </div>
    </main>

    <Footer />
  </Sidebar.Inset>
  <ToastHost />
</Sidebar.Provider>
