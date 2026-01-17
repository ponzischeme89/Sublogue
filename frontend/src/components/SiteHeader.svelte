<script>
  import ThemeSelector from "./ThemeSelector.svelte";
  import { Button } from "../lib/components/ui/button";
  import { Separator } from "../lib/components/ui/separator";
  import { Menu } from "lucide-svelte";

  export let title = "Scanner";
  export let showSidebarButton = false;
  export let onShowSidebar;
</script>

<header
  class="sticky top-0 z-40 flex h-[--header-height] items-center border-b border-border bg-background/80 backdrop-blur"
>
  <div class="flex w-full items-center justify-between px-4 sm:px-6">
    <div class="flex items-center gap-3">
      {#if showSidebarButton}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          on:click={onShowSidebar}
          aria-label="Show sidebar"
        >
          <Menu class="h-4 w-4" />
        </Button>
      {/if}
      <h2 class="text-base font-semibold tracking-tight">{title}</h2>
      <Separator orientation="vertical" className="hidden h-4 sm:block" />
      <span class="hidden text-xs text-muted-foreground sm:inline">
        Subtitle metadata workflow
      </span>
    </div>

    <div class="flex items-center gap-2">
      <ThemeSelector />
      <Separator orientation="vertical" className="mx-2 hidden h-4 sm:block" />
      <Button
        variant="ghost"
        size="sm"
        className="hidden text-muted-foreground sm:inline-flex"
        href="https://github.com/yourusername/sublogue"
        target="_blank"
        rel="noopener noreferrer"
      >
        GitHub
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="hidden text-muted-foreground sm:inline-flex"
        href="https://discord.gg/your-invite"
        target="_blank"
        rel="noopener noreferrer"
      >
        Discord
      </Button>
    </div>
  </div>
</header>
