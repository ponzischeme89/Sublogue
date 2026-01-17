<script>
  import { cn } from '../../../utils.js'

  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

<thead class={cn('[&_tr]:border-b', className, restClass)} {...restProps}>
  <slot />
</thead>
