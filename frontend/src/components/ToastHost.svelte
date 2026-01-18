<script>
  import { fly } from 'svelte/transition'
  import { toasts, removeToast } from '../lib/toastStore.js'
  import { X } from 'lucide-svelte'

  const toneStyles = {
    info: 'border-white/10 bg-bg-card text-text-primary',
    success: 'border-emerald-500/50 bg-emerald-900/60 text-emerald-50',
    error: 'border-red-500/30 bg-red-500/10 text-red-100'
  }
</script>

<div class="fixed right-4 top-4 z-50 space-y-2">
  {#each $toasts as toast (toast.id)}
    <div
      class={`flex items-center gap-3 rounded-xl border px-4 py-3 text-[12px] shadow-[0_12px_30px_rgba(0,0,0,0.35)] ${toneStyles[toast.tone] || toneStyles.info}`}
      in:fly={{ y: -8, duration: 160 }}
      out:fly={{ y: -8, duration: 160 }}
      role="status"
    >
      <span class="flex-1">{toast.message}</span>
      <button
        class="text-text-tertiary hover:text-white transition-colors"
        on:click={() => removeToast(toast.id)}
        aria-label="Dismiss notification"
      >
        <X class="h-3.5 w-3.5" />
      </button>
    </div>
  {/each}
</div>
