<script>
  import { cn } from '../../../utils.js'

  export let orientation = 'horizontal'
  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)

  $: isVertical = orientation === 'vertical'
</script>

<div
  role="separator"
  aria-orientation={orientation}
  class={cn(
    'shrink-0 bg-border',
    isVertical ? 'h-full w-px' : 'h-px w-full',
    className,
    restClass,
  )}
  {...restProps}
></div>
