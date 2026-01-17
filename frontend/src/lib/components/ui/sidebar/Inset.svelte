<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<div class={cn('flex min-h-screen flex-1 flex-col', className, restClass)} {...restProps}>
  <slot />
</div>
