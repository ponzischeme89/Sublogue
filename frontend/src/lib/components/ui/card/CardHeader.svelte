<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<div class={cn('flex flex-col space-y-1.5 p-6', className, restClass)} {...restProps}>
  <slot />
</div>
