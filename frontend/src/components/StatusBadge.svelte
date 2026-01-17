<script>
  import { Check } from 'lucide-svelte'

  export let status = 'Not Loaded'

  const statusStyles = {
    'Has Plot': 'bg-gray-500/20 text-gray-300',
    'Processed': 'bg-green-500/20 text-green-400',
    'Not Loaded': 'bg-gray-500/10 text-gray-400 border-gray-500/20',
    'Error': 'bg-red-500/10 text-red-400 border-red-500/20',
    'Skipped': 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    'Processing': 'bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse'
  }

  $: classes = statusStyles[status] || statusStyles['Not Loaded']
  $: hasIcon = status === 'Has Plot' || status === 'Processed'
</script>

{#if hasIcon}
  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-medium rounded-full {classes}">
    <Check class="w-3 h-3" />
    {status}
  </span>
{:else}
  <span class="inline-flex px-2 py-0.5 text-xs font-medium rounded border {classes}">
    {status}
  </span>
{/if}
