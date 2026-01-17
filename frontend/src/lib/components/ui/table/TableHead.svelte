<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<th
  class={cn(
    'h-12 px-4 text-left align-middle text-xs font-medium text-muted-foreground',
    className,
    restClass,
  )}
  {...restProps}
>
  <slot />
</th>
