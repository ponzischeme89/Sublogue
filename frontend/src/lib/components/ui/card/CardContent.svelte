<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<div class={cn('p-6 pt-0', className, restClass)} {...restProps}>
  <slot />
</div>
