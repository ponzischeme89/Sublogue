<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<div
  class={cn('flex min-h-screen w-full bg-background text-foreground', className, restClass)}
  {...restProps}
>
  <slot />
</div>
