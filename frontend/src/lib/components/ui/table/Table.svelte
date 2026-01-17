<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<table class={cn('w-full caption-bottom text-sm', className, restClass)} {...restProps}>
  <slot />
</table>
