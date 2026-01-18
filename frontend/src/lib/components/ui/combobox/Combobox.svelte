<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte'
  import { Button } from '../button'
  import { Input } from '../input'
  import { cn } from '../../../utils.js'

  const dispatch = createEventDispatcher()

  export let items = []
  export let value = ''
  export let placeholder = 'Select...'
  export let disabled = false
  export let className = ''
  export let searchable = true
  export let dropup = false
  export let displayPrefix = ''

  let open = false
  let search = ''
  let root
  let hoveredDisabled = null
  let tooltipPosition = { x: 0, y: 0 }

  const getLabel = (itemValue) =>
    items.find((item) => item.value === itemValue)?.label

  $: selectedLabel = getLabel(value)
  $: filteredItems = searchable
    ? items.filter((item) => {
        const haystack = `${item.label} ${item.description || ''}`.toLowerCase()
        return haystack.includes(search.toLowerCase())
      })
    : items

  function toggle() {
    if (!disabled) open = !open
  }

  function selectItem(itemValue) {
    dispatch('change', { value: itemValue })
    open = false
    search = ''
  }

  function handleKeydown(event) {
    if (event.key === 'Escape') open = false
  }

  function handleOutsideClick(event) {
    if (root && !root.contains(event.target)) {
      open = false
    }
  }

  onMount(() => {
    document.addEventListener('mousedown', handleOutsideClick, true)
    document.addEventListener('keydown', handleKeydown, true)
  })

  onDestroy(() => {
    document.removeEventListener('mousedown', handleOutsideClick, true)
    document.removeEventListener('keydown', handleKeydown, true)
  })

  function showDisabledTooltip(event, item) {
    if (!item.disabled) return
    const rect = event.currentTarget.getBoundingClientRect()
    hoveredDisabled = item.value
    tooltipPosition = {
      x: rect.right + 10,
      y: rect.top + rect.height / 2
    }
  }

  function hideDisabledTooltip() {
    hoveredDisabled = null
  }
</script>

<div class={cn('relative', className)} bind:this={root}>
  <Button
    variant="outline"
    size="sm"
    className="h-10 w-full justify-between gap-2 px-4"
    on:click={toggle}
    {disabled}
  >
    <span class="flex items-center gap-2">
      <slot name="icon" />
      <span class={selectedLabel ? 'text-foreground' : 'text-muted-foreground'}>
        {selectedLabel ? `${displayPrefix}${selectedLabel}` : placeholder}
      </span>
    </span>
    <svg
      class="h-3.5 w-3.5 text-text-tertiary transition-transform {open
        ? 'rotate-180'
        : ''}"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M19 9l-7 7-7-7"
      />
    </svg>
  </Button>

  {#if open}
    <div
      class="absolute left-0 min-w-[220px] w-[92%] rounded-lg border border-border bg-card shadow-2xl overflow-hidden z-50 {dropup
        ? 'bottom-full mb-2'
        : 'top-full mt-2'}"
    >
      {#if searchable}
        <div class="p-2 border-b border-border bg-muted/40">
          <Input
            value={search}
            on:input={(e) => (search = e.target.value)}
            placeholder="Search..."
            className="h-9 text-[12px]"
          />
        </div>
      {/if}
      <div class="max-h-56 overflow-y-auto py-1">
        {#if filteredItems.length === 0}
          <div class="px-4 py-3 text-xs text-text-tertiary">
            No results found.
          </div>
        {:else}
          {#each filteredItems as item}
            <button
              type="button"
              class="relative w-full px-4 py-2.5 text-left transition-colors flex items-center justify-between {item.disabled ? 'opacity-40 cursor-not-allowed' : 'hover:bg-bg-hover'}"
              disabled={item.disabled}
              on:click={() => !item.disabled && selectItem(item.value)}
              on:mouseenter={(event) => showDisabledTooltip(event, item)}
              on:mouseleave={hideDisabledTooltip}
            >
              <div>
                <div class="text-[13px] font-medium">{item.label}</div>
                {#if item.description}
                  <div class="text-[11px] text-text-tertiary">
                    {item.description}
                  </div>
                {/if}
              </div>
              {#if item.value === value}
                <svg
                  class="h-4 w-4 text-accent"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              {/if}
            </button>
          {/each}
        {/if}
      </div>
    </div>
    {#if hoveredDisabled}
      <div
        class="pointer-events-none fixed z-50 whitespace-nowrap rounded-lg border border-white/10 bg-bg-card px-4 py-2.5 text-[11px] text-text-secondary shadow-[0_12px_30px_rgba(0,0,0,0.35)]"
        style="left: {tooltipPosition.x}px; top: {tooltipPosition.y}px; transform: translateY(-50%);"
      >
        Enable this in Settings under Integrations.
      </div>
    {/if}
  {/if}
</div>
