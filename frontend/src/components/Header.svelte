<script>
  import ThemeSelector from "./ThemeSelector.svelte";
  import { Button } from "../lib/components/ui/button";
  import { Separator } from "../lib/components/ui/separator";
  import {
    Github,
    History,
    Menu,
    MessageCircle,
    Scan,
    Settings,
    X
  } from "lucide-svelte";

  export let currentView = "scanner";
  export let onNavigate;

  let mobileMenuOpen = false;

  function navigateTo(view) {
    onNavigate(view);
    mobileMenuOpen = false;
  }

  function toggleMobileMenu() {
    mobileMenuOpen = !mobileMenuOpen;
  }
</script>

<header
  class="sticky top-0 z-50 border-b border-border backdrop-blur bg-background/80"
>
  <div class="max-w-7xl mx-auto px-6 md:px-8 py-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl md:text-lg font-bold tracking-tight">Sublogue</h1>

      <!-- Desktop Navigation -->
      <nav class="hidden md:flex items-center gap-1.5">
        <Button
          variant={currentView === "scanner" ? "secondary" : "ghost"}
          size="sm"
          className="gap-1.5"
          on:click={() => navigateTo("scanner")}
        >
          <Scan class="w-3.5 h-3.5" />
          <span class="text-[13px]">Scanner</span>
        </Button>

        <Button
          variant={currentView === "history" ? "secondary" : "ghost"}
          size="sm"
          className="gap-1.5"
          on:click={() => navigateTo("history")}
        >
          <History class="w-3.5 h-3.5" />
          <span class="text-[13px]">History</span>
        </Button>

        <Button
          variant={currentView === "settings" ? "secondary" : "ghost"}
          size="sm"
          className="gap-1.5"
          on:click={() => navigateTo("settings")}
        >
          <Settings class="w-3.5 h-3.5" />
          <span class="text-[13px]">Settings</span>
        </Button>

        <Separator orientation="vertical" className="mx-2 h-4" />

        <ThemeSelector />

        <Separator orientation="vertical" className="mx-2 h-4" />

        <a
          href="https://discord.gg/your-invite"
          target="_blank"
          rel="noopener noreferrer"
          class="p-1.5 text-text-secondary hover:text-text-primary transition-colors"
          aria-label="Discord"
        >
          <MessageCircle class="w-4 h-4" />
        </a>

        <a
          href="https://github.com/yourusername/sublogue"
          target="_blank"
          rel="noopener noreferrer"
          class="p-1.5 text-text-secondary hover:text-text-primary transition-colors"
          aria-label="GitHub"
        >
          <Github class="w-4 h-4" />
        </a>

        <Separator orientation="vertical" className="mx-2 h-4" />

        <span class="text-[11px] text-text-tertiary px-2">v1.0.1</span>
      </nav>

      <!-- Mobile Menu Button -->
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        on:click={toggleMobileMenu}
        aria-label="Toggle menu"
      >
        {#if mobileMenuOpen}
          <X class="w-6 h-6" />
        {:else}
          <Menu class="w-6 h-6" />
        {/if}
      </Button>
    </div>

    <!-- Mobile Menu -->
    {#if mobileMenuOpen}
      <nav class="md:hidden mt-6 flex flex-col gap-2">
        <div class="flex items-center gap-2 px-4 py-2 mb-2">
          <span
            class="text-[11px] text-text-tertiary font-medium uppercase tracking-wider"
            >Theme</span
          >
          <div class="ml-auto">
            <ThemeSelector />
          </div>
        </div>

        <Button
          variant={currentView === "scanner" ? "secondary" : "ghost"}
          className="w-full justify-start gap-3 px-4 py-3"
          on:click={() => navigateTo("scanner")}
        >
          <Scan class="w-5 h-5" />
          <span class="text-sm font-medium">Scanner</span>
        </Button>

        <Button
          variant={currentView === "history" ? "secondary" : "ghost"}
          className="w-full justify-start gap-3 px-4 py-3"
          on:click={() => navigateTo("history")}
        >
          <History class="w-5 h-5" />
          <span class="text-sm font-medium">History</span>
        </Button>

        <Button
          variant={currentView === "settings" ? "secondary" : "ghost"}
          className="w-full justify-start gap-3 px-4 py-3"
          on:click={() => navigateTo("settings")}
        >
          <Settings class="w-5 h-5" />
          <span class="text-sm font-medium">Settings</span>
        </Button>
      </nav>
    {/if}
  </div>
</header>
