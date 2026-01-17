<script>
  import { onMount } from 'svelte'
  import { cn } from '../../../utils.js'

  export let className = ''
  export let skeletonFlash = true
  let restClass
  let restProps = {}
  let showSkeleton = false

  $: ({ class: restClass, ...restProps } = $$restProps)

  onMount(() => {
    if (!skeletonFlash) return
    showSkeleton = true
    const timer = setTimeout(() => {
      showSkeleton = false
    }, 900)
    return () => clearTimeout(timer)
  })
</script>

<div
  class={cn(
    'rounded-lg border border-border bg-card text-card-foreground shadow-sm',
    showSkeleton ? 'relative overflow-hidden' : '',
    className,
    restClass
  )}
  {...restProps}
>
  <slot />
  {#if showSkeleton}
    <div class="pointer-events-none absolute inset-0 bg-[color:var(--bg-hover)] opacity-40 animate-pulse"></div>
  {/if}
</div>
