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

  const navItems = [
    { id: "scanner", label: "Scanner", icon: Scan },
    { id: "automation", label: "Automations", icon: Zap },
    { id: "history", label: "History", icon: History },
    { id: "library", label: "Library", icon: Library },
    { id: "settings", label: "Settings", icon: Settings },
  ];
</script>

<aside
  class={`fixed inset-y-0 left-0 z-40 h-screen w-[--sidebar-width] border-r border-border bg-[color:var(--bg-secondary)] text-text-primary transition-transform duration-200 ease-out md:sticky md:top-0 flex flex-col ${
    !open && isMobile
      ? "-translate-x-full pointer-events-none"
      : "translate-x-0"
  }`}
>
  <!-- Logo area -->
  <div
    class={`relative flex items-center gap-3 py-5 border-b border-border ${collapsed ? "px-2 justify-center" : "px-4"}`}
  >
    {#if collapsed}
      <div class="h-8 w-8 rounded-lg overflow-hidden">
        <img
          src={sublogueLogo}
          alt="Sublogue"
          class="h-full w-full object-cover"
        />
      </div>
    {:else}
      <div class="flex items-center -ml-5 flex-1 min-w-0">
        <img
          src={sublogueLogo}
          alt="Sublogue"
          class="h-8 w-auto max-w-[200px] object-contain"
        />
      </div>
    {/if}
    <button
      class="shrink-0 h-7 w-7 rounded-lg flex items-center justify-center text-text-tertiary hover:text-text-primary hover:bg-bg-hover transition-all duration-150"
      on:click={onToggleSidebar}
      aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
    >
      {#if collapsed}
        <ChevronRight class="h-3.5 w-3.5" />
      {:else}
        <ChevronLeft class="h-3.5 w-3.5" />
      {/if}
    </button>
  </div>

  <!-- Navigation -->
  <nav
    class={`flex-1 min-h-0 overflow-y-auto py-3 space-y-0.5 ${collapsed ? "px-2" : "px-2"}`}
  >
    {#each navItems as item}
      {@const isActive = currentView === item.id}
      <button
        class={`w-full flex items-center gap-2.5 rounded-lg text-[13px] font-medium transition-all duration-150 relative
          ${collapsed ? "justify-center px-0 h-9" : "px-3 h-9"}
          ${
            isActive
              ? "bg-bg-hover text-text-primary"
              : "text-text-secondary hover:text-text-primary hover:bg-bg-hover/60"
          }`}
        on:click={() => onNavigate(item.id)}
        aria-current={isActive ? "page" : undefined}
      >
        {#if isActive && !collapsed}
          <span
            class="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-full bg-accent"
          ></span>
        {/if}
        <svelte:component this={item.icon} class="h-4 w-4 shrink-0" />
        {#if !collapsed}
          <span>{item.label}</span>
        {/if}
      </button>
    {/each}
  </nav>

  <!-- Footer -->
  <div
    class={`border-t border-border pb-4 pt-3 space-y-2 ${collapsed ? "px-2" : "px-2"}`}
  >
    {#if !collapsed}
      <div class="px-1">
        <ThemeSelector className="w-full" />
      </div>
    {/if}
    <div
      class={`flex items-center px-1 ${collapsed ? "justify-center" : "justify-between"}`}
    >
      {#if !collapsed}
        <span class="text-[11px] text-text-tertiary"
          >&copy; 2026 ponzischeme89</span
        >
        <div class="flex items-center gap-2">
          <Badge
            variant="outline"
            class="text-[10px] text-text-tertiary border-border py-0"
            >v1.1.4</Badge
          >
          <a
            href="https://github.com/ponzischeme89/Sublogue"
            target="_blank"
            rel="noopener noreferrer"
            class="text-text-tertiary hover:text-text-primary transition-colors"
            aria-label="GitHub"
          >
            <Github class="h-3.5 w-3.5" />
          </a>
        </div>
      {:else}
        <a
          href="https://github.com/ponzischeme89/Sublogue"
          target="_blank"
          rel="noopener noreferrer"
          class="text-text-tertiary hover:text-text-primary transition-colors"
          aria-label="GitHub"
        >
          <Github class="h-3.5 w-3.5" />
        </a>
      {/if}
    </div>
  </div>
</aside>

<style>
  nav button {
    letter-spacing: -0.01em;
  }
</style>
