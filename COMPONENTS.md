# Component Reference

Complete guide to all Svelte components in SubPlotter.

---

## App.svelte

**Location**: `frontend/src/App.svelte`

Main application component with layout and routing.

### Features
- Tab-based navigation (Scanner / Settings)
- Health check on mount
- API configuration warning banner
- Gradient header with branding
- Responsive footer

### State
```javascript
currentView: 'scanner' | 'settings'
apiConfigured: boolean
selectedFiles: string[]
scanPanelKey: number  // Forces refresh after processing
```

### Routing
Simple state-based routing - no router library needed:
```javascript
function navigateTo(view) {
  currentView = view
}
```

### Styling
- Purple gradient header
- Dark mode support
- Responsive breakpoints at 768px
- Max width: 1200px

---

## SettingsPanel.svelte

**Location**: `frontend/src/components/SettingsPanel.svelte`

Configuration interface for API keys and behavior.

### Props
None (standalone component)

### Features
- API key input (password type)
- Directory path input
- Duration numeric input
- Load settings on mount
- Save with feedback messages
- Loading and error states

### State
```javascript
apiKey: string
defaultDirectory: string
duration: number
loading: boolean
saving: boolean
error: string | null
successMessage: string | null
```

### API Calls
- `getSettings()` on mount
- `updateSettings()` on save

### Usage
```svelte
<SettingsPanel />
```

---

## ScanPanel.svelte

**Location**: `frontend/src/components/ScanPanel.svelte`

Directory scanning interface with results display.

### Props (Exported)
```javascript
selectedFilePaths: string[]  // Bind to get selected files
```

### Features
- Directory input field
- Start scan button
- Scanning progress indicator
- Last scan timestamp
- File count display
- Integrates MovieList component
- Loads previous scan results on mount

### State
```javascript
directory: string
files: FileInfo[]
scanning: boolean
error: string | null
lastScan: string | null
selectedFilePaths: string[]
```

### API Calls
- `getSettings()` on mount (for default directory)
- `getScanStatus()` on mount (load cached results)
- `startScan(directory)` on button click

### Usage
```svelte
<script>
  let selected = []
</script>

<ScanPanel bind:selectedFilePaths={selected} />
```

### File Format
```javascript
{
  path: string,
  name: string,
  has_plot: boolean,
  status: string,
  summary: string,
  selected: boolean
}
```

---

## MovieList.svelte

**Location**: `frontend/src/components/MovieList.svelte`

Display and selection of scanned movie files.

### Props
```javascript
files: FileInfo[]  // Array of file objects
onSelectionChange: (selectedPaths: string[]) => void
```

### Features
- Empty state message
- Select all checkbox
- Individual file checkboxes
- File name display
- Status badges
- Summary preview (truncated to 100 chars)
- Selected count in header
- Scrollable list (max-height: 500px)

### Methods
```javascript
toggleSelection(file)  // Toggle individual file
toggleAll()            // Toggle all files
formatSummary(summary) // Truncate long summaries
```

### Usage
```svelte
<MovieList
  {files}
  onSelectionChange={(paths) => console.log(paths)}
/>
```

### Styling
- Hover effects on rows
- Selected rows highlighted (blue tint)
- Dark mode support

---

## ActionToolbar.svelte

**Location**: `frontend/src/components/ActionToolbar.svelte`

Processing controls and results display.

### Props
```javascript
selectedFiles: string[]  // Array of file paths
disabled: boolean        // Disable when no API key
```

### Events
```javascript
'complete'  // Dispatched after successful processing
            // Detail: { results: ProcessResult[] }
```

### Features
- Large prominent action button
- Shows selected file count
- Confirmation modal before processing
- Results modal after processing
- Success/failure statistics
- Individual result breakdown
- Error handling and display

### State
```javascript
processing: boolean
showConfirmation: boolean
duration: number
results: ProcessResult[] | null
error: string | null
```

### Modals
**Confirmation Modal**:
- File count display
- Warning about file modification
- Backup information
- Cancel / Confirm buttons

**Results Modal**:
- Success/failure counts
- Per-file results list
- Color-coded success/failure
- Close button

### API Calls
- `getSettings()` before processing (get duration)
- `processFiles(files, duration)` on confirm

### Usage
```svelte
<ActionToolbar
  {selectedFiles}
  disabled={!apiConfigured}
  on:complete={handleComplete}
/>
```

---

## StatusBadge.svelte

**Location**: `frontend/src/components/StatusBadge.svelte`

Reusable status indicator component.

### Props
```javascript
status: string  // Default: 'Not Loaded'
```

### Supported Statuses
- `'Has Plot'` - Green (file already processed)
- `'Processed'` - Green (just processed)
- `'Not Loaded'` - Gray (not yet processed)
- `'Error'` - Red (processing failed)
- `'Skipped'` - Yellow (skipped, e.g., already has plot)
- `'Processing'` - Blue with pulse animation

### Styling
- Rounded badge design
- Color-coded by status
- Dark mode variants
- Pulse animation for processing state

### Usage
```svelte
<StatusBadge status="Has Plot" />
<StatusBadge status="Processing" />
<StatusBadge status="Error" />
```

---

## Component Hierarchy

```
App.svelte
├── SettingsPanel.svelte (when currentView === 'settings')
└── (when currentView === 'scanner')
    ├── ScanPanel.svelte
    │   └── MovieList.svelte
    │       └── StatusBadge.svelte (multiple instances)
    └── ActionToolbar.svelte
```

---

## Common Patterns

### Loading States
```svelte
{#if loading}
  <div class="loading">Loading...</div>
{:else}
  <!-- Content -->
{/if}
```

### Error Display
```svelte
{#if error}
  <div class="message message-error">{error}</div>
{/if}
```

### Success Messages
```svelte
{#if successMessage}
  <div class="message message-success">{successMessage}</div>
{/if}
```

### Modal Pattern
```svelte
{#if showModal}
  <div class="modal-overlay" on:click={closeModal}>
    <div class="modal" on:click|stopPropagation>
      <!-- Modal content -->
    </div>
  </div>
{/if}
```

### Reactive Statements
```svelte
$: selectedCount = files.filter(f => f.selected).length
$: hasSelection = selectedFiles.length > 0
```

---

## Styling Guidelines

### Color Palette
- Primary: `#3b82f6` (blue)
- Success: `#d1fae5` / `#065f46` (green)
- Error: `#fee2e2` / `#991b1b` (red)
- Warning: `#fef3c7` / `#92400e` (yellow)
- Processing: `#dbeafe` / `#1e40af` (blue)

### Dark Mode
All components support dark mode via:
```css
@media (prefers-color-scheme: dark) {
  /* Dark styles */
}
```

### Layout
- Container max-width: 1200px
- Standard padding: 2rem (desktop), 1rem (mobile)
- Standard gap: 0.5rem to 1rem
- Border radius: 6px (small), 8px (large)

### Transitions
- Duration: 150ms to 200ms
- Timing: `cubic-bezier(0.4, 0, 0.2, 1)`
- Properties: background, border, color

---

## Component Communication

### Parent → Child (Props)
```svelte
<MovieList {files} disabled={true} />
```

### Child → Parent (Events)
```svelte
<!-- Child -->
<script>
  import { createEventDispatcher } from 'svelte'
  const dispatch = createEventDispatcher()

  function handleClick() {
    dispatch('complete', { data: 'value' })
  }
</script>

<!-- Parent -->
<ActionToolbar on:complete={handleComplete} />
```

### Two-Way Binding
```svelte
<ScanPanel bind:selectedFilePaths={selected} />
```

### Callbacks
```svelte
<MovieList onSelectionChange={(paths) => { ... }} />
```

---

## Best Practices

1. **Keep components small** - Each component does one thing well
2. **Explicit state** - No hidden state or magic
3. **Clear props** - Document all props and their types
4. **Error handling** - Always handle loading and error states
5. **Accessibility** - Use semantic HTML and labels
6. **Responsive** - Test at mobile and desktop sizes
7. **Dark mode** - Support system preference
8. **No external state** - Use props and events, not stores

---

## Adding New Components

Template for new component:

```svelte
<script>
  /**
   * ComponentName - Brief description
   * Props:
   *   propName: type - description
   */
  import { onMount } from 'svelte'

  export let propName = 'default'

  let loading = false
  let error = null

  onMount(async () => {
    // Initialization
  })

  async function handleAction() {
    loading = true
    error = null

    try {
      // API call or logic
    } catch (err) {
      error = err.message
    } finally {
      loading = false
    }
  }
</script>

<div class="component-name">
  {#if loading}
    <div class="loading">Loading...</div>
  {:else if error}
    <div class="error">{error}</div>
  {:else}
    <!-- Content -->
  {/if}
</div>

<style>
  .component-name {
    /* Styles */
  }

  /* Dark mode */
  @media (prefers-color-scheme: dark) {
    /* Dark styles */
  }
</style>
```

---

## Testing Components

While no test framework is included, you can test:

1. **Manually** - Run dev server and interact
2. **Browser DevTools** - Check props and state
3. **Console logs** - Add temporary logging
4. **Network tab** - Verify API calls
5. **Error scenarios** - Test with invalid data

For automated testing, consider:
- Vitest + Svelte Testing Library
- Playwright for E2E tests
