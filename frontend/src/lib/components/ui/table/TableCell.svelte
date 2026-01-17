<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<td
  class={cn('p-4 align-middle [&:has([role=checkbox])]:pr-0', className, restClass)}
  {...restProps}
>
  <slot />
</td>
