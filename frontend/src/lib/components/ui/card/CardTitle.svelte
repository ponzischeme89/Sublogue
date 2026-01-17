<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<h3
  class={cn('text-lg font-semibold leading-none tracking-tight', className, restClass)}
  {...restProps}
>
  <slot />
</h3>
