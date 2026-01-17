<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<div
  class={cn('animate-pulse rounded-md bg-[color:var(--bg-hover)] opacity-50', className, restClass)}
  {...restProps}
></div>
