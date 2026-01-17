<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<tbody class={cn('[&_tr:last-child]:border-0', className, restClass)} {...restProps}>
  <slot />
</tbody>
