<script>
  import { Button } from "../lib/components/ui/button";
  import { Separator } from "../lib/components/ui/separator";
  import { Badge } from "../lib/components/ui/badge";
  import {
    ChevronLeft,
    ChevronRight,
    Github,
    Scan,
    Settings,
    History,
    Library,
    Zap,
  } from "lucide-svelte";
  import ThemeSelector from "./ThemeSelector.svelte";
  import sublogueLogo from "../assets/sublogue_v2.png";

  export let currentView = "scanner";
  export let onNavigate;
  export let onToggleSidebar;
  export let open = true;
  export let collapsed = false;
  export let isMobile = false;
</script>

<aside
  class={`fixed inset-y-0 left-0 z-40 h-screen w-[--sidebar-width] border-r border-border bg-[color:var(--bg-primary)] bg-gradient-to-b from-white/12 via-white/5 to-transparent text-text-primary transition-transform duration-200 ease-out md:sticky md:top-0 ${
    !open && isMobile
      ? "-translate-x-full pointer-events-none"
      : "translate-x-0"
  }`}
>
  <div class="flex h-full min-h-0 flex-col">
    <div
      class={`relative flex items-center gap-3 py-5 ${collapsed ? "px-2" : "px-4"}`}
    >
      {#if collapsed}
        <div
          class="relative flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-black/40 overflow-hidden"
        >
          <span class="absolute inset-0 rounded-lg bg-blue-500/10 blur-md"
          ></span>

          <img
            src={sublogueLogo}
            alt="Sublogue"
            class="relative h-full w-full object-cover"
          />
        </div>
      {:else}
        <div class="flex items-center -ml-6">
          <img
            src={sublogueLogo}
            alt="Sublogue"
            class="h-9 w-auto max-w-[220px] object-contain"
          />
        </div>
      {/if}
      <button
        class="absolute right-3 top-1/2 -translate-y-1/2 h-8 w-8 rounded-full border border-white/10 bg-white/5 text-text-secondary hover:text-white hover:bg-[color:var(--bg-hover)] transition-colors"
        on:click={onToggleSidebar}
        aria-label={collapsed ? "Show sidebar" : "Hide sidebar"}
      >
        {#if collapsed}
          <ChevronRight class="h-4 w-4 mx-auto" />
        {:else}
          <ChevronLeft class="h-4 w-4 mx-auto" />
        {/if}
      </button>
    </div>

    <nav
      class={`sidebar-nav flex-1 min-h-0 overflow-y-auto py-3 ${collapsed ? "px-1.5" : "px-3"} space-y-1`}
    >
      <Button
        variant="ghost"
        className={`w-full rounded-md py-1.5 text-[13px] font-semibold leading-none ${
          collapsed ? "justify-center px-0" : "justify-start px-2 gap-2"
        } ${
          currentView === "scanner"
            ? "bg-[color:var(--bg-hover)] text-white font-bold"
            : "text-text-secondary hover:text-white hover:bg-[color:var(--bg-hover)]"
        }`}
        on:click={() => onNavigate("scanner")}
        aria-current={currentView === "scanner" ? "page" : undefined}
      >
        <Scan class="h-4 w-4" />
        {#if !collapsed}
          Scanner
        {/if}
      </Button>

      <Button
        variant="ghost"
        className={`w-full rounded-md py-1.5 text-[13px] font-semibold leading-none ${
          collapsed ? "justify-center px-0" : "justify-start px-2 gap-2"
        } ${
          currentView === "automation"
            ? "bg-[color:var(--bg-hover)] text-white font-bold"
            : "text-text-secondary hover:text-white hover:bg-[color:var(--bg-hover)]"
        }`}
        on:click={() => onNavigate("automation")}
        aria-current={currentView === "automation" ? "page" : undefined}
      >
        <Zap class="h-4 w-4" />
        {#if !collapsed}
          Automations
        {/if}
      </Button>

      <Button
        variant="ghost"
        className={`w-full rounded-md py-1.5 text-[13px] font-semibold leading-none ${
          collapsed ? "justify-center px-0" : "justify-start px-2 gap-2"
        } ${
          currentView === "history"
            ? "bg-[color:var(--bg-hover)] text-white font-bold"
            : "text-text-secondary hover:text-white hover:bg-[color:var(--bg-hover)]"
        }`}
        on:click={() => onNavigate("history")}
        aria-current={currentView === "history" ? "page" : undefined}
      >
        <History class="h-4 w-4" />
        {#if !collapsed}
          History
        {/if}
      </Button>

      <Button
        variant="ghost"
        className={`w-full rounded-md py-1.5 text-[13px] font-semibold leading-none ${
          collapsed ? "justify-center px-0" : "justify-start px-2 gap-2"
        } ${
          currentView === "library"
            ? "bg-[color:var(--bg-hover)] text-white font-bold"
            : "text-text-secondary hover:text-white hover:bg-[color:var(--bg-hover)]"
        }`}
        on:click={() => onNavigate("library")}
        aria-current={currentView === "library" ? "page" : undefined}
      >
        <Library class="h-4 w-4" />
        {#if !collapsed}
          Library
        {/if}
      </Button>

      <Button
        variant="ghost"
        className={`w-full rounded-md py-1.5 text-[13px] font-semibold leading-none ${
          collapsed ? "justify-center px-0" : "justify-start px-2 gap-2"
        } ${
          currentView === "settings"
            ? "bg-[color:var(--bg-hover)] text-white font-bold"
            : "text-text-secondary hover:text-white hover:bg-[color:var(--bg-hover)]"
        }`}
        on:click={() => onNavigate("settings")}
        aria-current={currentView === "settings" ? "page" : undefined}
      >
        <Settings class="h-4 w-4" />
        {#if !collapsed}
          Settings
        {/if}
      </Button>
    </nav>

    <div class={`pb-5 space-y-3 ${collapsed ? "px-2" : "px-3"}`}>
      <Separator className="bg-white/10" />
      {#if !collapsed}
        <ThemeSelector className="w-full" />
      {/if}
      <div
        class={`flex items-center px-3 py-2 text-xs ${collapsed ? "justify-center" : "justify-between"}`}
      >
        {#if !collapsed}
          <Badge className="text-text-secondary">Version: v1.1.0</Badge>
        {:else}
          <Badge className="text-text-secondary">v</Badge>
        {/if}
      </div>
      <div
        class={`flex items-center px-3 py-2 text-xs ${collapsed ? "justify-center" : "justify-between"}`}
      >
        {#if !collapsed}
          <span class="text-text-tertiary">&copy; 2026 ponzischeme89</span>
          <a
            href="https://github.com/ponzischeme89/Sublogue"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center text-text-tertiary hover:text-white transition-colors"
            aria-label="GitHub"
          >
            <Github class="h-4 w-4" />
          </a>
        {:else}
          <span class="text-text-tertiary">&copy;</span>
        {/if}
      </div>
    </div>
  </div>
</aside>

<style>
  .sidebar-nav {
    letter-spacing: -0.01em;
  }
</style>
