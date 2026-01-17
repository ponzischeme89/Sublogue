<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<tfoot
  class={cn('bg-muted/50 font-medium [&>tr]:last:border-b-0', className, restClass)}
  {...restProps}
>
  <slot />
</tfoot>
