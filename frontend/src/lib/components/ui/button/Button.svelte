<script>
  import { createEventDispatcher } from 'svelte'
  import { cva } from 'class-variance-authority'
  import { cn } from '../../../utils.js'

  const dispatch = createEventDispatcher()

  const buttonVariants = cva(
    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
    {
      variants: {
        variant: {
          default: 'bg-primary text-primary-foreground hover:bg-primary/90',
          secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
          outline: 'border border-input bg-background hover:bg-accent/10 hover:text-foreground',
          ghost: 'hover:bg-accent/10 hover:text-foreground',
          link: 'text-primary underline-offset-4 hover:underline',
          destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        },
        size: {
          default: 'h-10 px-4 py-2',
          sm: 'h-9 px-3',
          lg: 'h-11 px-6',
          icon: 'h-10 w-10',
        },
      },
      defaultVariants: {
        variant: 'default',
        size: 'default',
      },
    },
  )

  export let variant = 'default'
  export let size = 'default'
  export let type = 'button'
  export let href = null
  export let className = ''
  let restClass
  let restProps = {}

  $: ({ class: restClass, ...restProps } = $$restProps)
</script>

{#if href}
  <a
    href={href}
    class={cn(buttonVariants({ variant, size }), className, restClass)}
    on:click={(event) => dispatch('click', event)}
    {...restProps}
  >
    <slot />
  </a>
{:else}
  <button
    type={type}
    class={cn(buttonVariants({ variant, size }), className, restClass)}
    on:click={(event) => dispatch('click', event)}
    {...restProps}
  >
    <slot />
  </button>
{/if}
