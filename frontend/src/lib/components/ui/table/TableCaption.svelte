<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<caption
  class={cn('mt-4 text-sm text-muted-foreground', className, restClass)}
  {...restProps}
>
  <slot />
</caption>
