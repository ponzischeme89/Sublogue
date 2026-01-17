<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<p class={cn('text-sm text-muted-foreground', className, restClass)} {...restProps}>
  <slot />
</p>
