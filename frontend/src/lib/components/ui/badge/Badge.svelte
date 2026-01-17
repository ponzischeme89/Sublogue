<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<span
  class={cn(
    'inline-flex items-center rounded-full border border-border px-2.5 py-0.5 text-xs font-semibold text-foreground/80',
    className,
    restClass,
  )}
  {...restProps}
>
  <slot />
</span>
