<script>
  import { currentTheme, themes } from '../lib/themeStore.js'
  import { Combobox } from '../lib/components/ui/combobox'
  import { Palette } from 'lucide-svelte'

  export let className = ''

  const themeItems = Object.entries(themes).map(([value, theme]) => ({
    value,
    label: theme.name
  }))

  function handleThemeChange(event) {
    currentTheme.setTheme(event.detail.value)
  }
</script>

<Combobox
  items={themeItems}
  value={$currentTheme}
  placeholder="Appearance"
  className={className}
  on:change={handleThemeChange}
>
  <svelte:fragment slot="icon">
    <Palette class="h-3.5 w-3.5 text-text-tertiary" />
  </svelte:fragment>
</Combobox>
