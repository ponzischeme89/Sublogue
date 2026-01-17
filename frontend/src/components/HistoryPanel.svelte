<script>
  import { onMount } from 'svelte'
  import { getRunHistory, getRunDetails, getScanHistory, getStatistics } from '../lib/api.js'
  import { Skeleton } from '../lib/components/ui/skeleton'
  import { Input } from '../lib/components/ui/input'
  import { Button } from '../lib/components/ui/button'
  import { Combobox } from '../lib/components/ui/combobox'
  import { ClipboardList, Search, X } from 'lucide-svelte'
  import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
  } from '../lib/components/ui/table'

  let processingRuns = []
  let scanHistory = []
  let statistics = null
  let loading = true
  let error = null
  let selectedRun = null
  let showRunDetails = false
  let loadingDetails = false
  let query = ''
  let statusFilter = 'all'
  let dateFrom = ''
  let dateTo = ''

  const statusOptions = [
    { value: 'all', label: 'All statuses' },
    { value: 'completed', label: 'Completed' },
    { value: 'in_progress', label: 'In progress' },
    { value: 'failed', label: 'Failed' }
  ]

  onMount(async () => {
    await loadData()
  })

  async function loadData() {
    loading = true
    error = null
    const loadingStart = Date.now()

    try {
      const [runsResponse, scansResponse, statsResponse] = await Promise.all([
        getRunHistory(100),
        getScanHistory(100),
        getStatistics()
      ])

      processingRuns = runsResponse.runs || []
      scanHistory = scansResponse.scans || []
      statistics = statsResponse.statistics || null
    } catch (err) {
      error = `Failed to load history: ${err.message}`
      console.error('Error loading history:', err)
    } finally {
      const elapsed = Date.now() - loadingStart
      const minDelayMs = 1200
      if (elapsed < minDelayMs) {
        await new Promise((resolve) => setTimeout(resolve, minDelayMs - elapsed))
      }
      loading = false
    }
  }

  async function viewRunDetails(runId) {
    loadingDetails = true
    showRunDetails = true

    try {
      const response = await getRunDetails(runId)
      selectedRun = response.run
    } catch (err) {
      error = `Failed to load run details: ${err.message}`
      console.error('Error loading run details:', err)
    } finally {
      loadingDetails = false
    }
  }

  function closeRunDetails() {
    showRunDetails = false
    selectedRun = null
  }

  function formatDate(isoString) {
    if (!isoString) return 'N/A'
    const date = new Date(isoString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  function formatDuration(seconds) {
    if (!seconds) return 'N/A'
    if (seconds < 60) return `${Math.round(seconds)}s`
    const minutes = Math.floor(seconds / 60)
    const secs = Math.round(seconds % 60)
    return `${minutes}m ${secs}s`
  }

  function formatScanDuration(ms) {
    if (!ms) return 'N/A'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  function getStatusColor(status) {
    switch (status) {
      case 'completed': return 'text-green-300'
      case 'in_progress': return 'text-blue-300'
      case 'failed': return 'text-red-300'
      default: return 'text-text-secondary'
    }
  }

  function isWithinDateRange(dateString) {
    if (!dateString) return false
    if (!dateFrom && !dateTo) return true
    const value = new Date(dateString).getTime()
    if (Number.isNaN(value)) return false
    if (dateFrom) {
      const fromValue = new Date(dateFrom).setHours(0, 0, 0, 0)
      if (value < fromValue) return false
    }
    if (dateTo) {
      const toValue = new Date(dateTo).setHours(23, 59, 59, 999)
      if (value > toValue) return false
    }
    return true
  }

  function applyDatePreset(days) {
    const now = new Date()
    const from = new Date()
    from.setDate(now.getDate() - days)
    dateFrom = from.toISOString().slice(0, 10)
    dateTo = now.toISOString().slice(0, 10)
  }

  $: summary = {
    totalRuns: statistics?.total_runs ?? processingRuns.length,
    completedRuns:
      statistics?.completed_runs ??
      processingRuns.filter((run) => run.status === 'completed').length,
    totalFiles:
      statistics?.total_files_processed ??
      processingRuns.reduce((sum, run) => sum + (run.total_files || 0), 0),
    successfulFiles:
      statistics?.successful_files ??
      processingRuns.reduce((sum, run) => sum + (run.successful_files || 0), 0),
    failedFiles:
      statistics?.failed_files ??
      processingRuns.reduce((sum, run) => sum + (run.failed_files || 0), 0)
  }

  $: successRate =
    summary.totalFiles > 0
      ? Math.round((summary.successfulFiles / summary.totalFiles) * 100)
      : 0
  $: filteredProcessingRuns = processingRuns.filter((run) => {
    const matchesQuery =
      !query ||
      String(run.id).includes(query) ||
      (run.status || '').toLowerCase().includes(query.toLowerCase())
    const matchesStatus = statusFilter === 'all' || run.status === statusFilter
    const matchesDate = isWithinDateRange(run.started_at)
    return matchesQuery && matchesStatus && matchesDate
  })
  $: filteredScanHistory = scanHistory.filter((scan) => {
    const matchesQuery =
      !query ||
      (scan.directory || '').toLowerCase().includes(query.toLowerCase()) ||
      String(scan.id).includes(query)
    const matchesDate = isWithinDateRange(scan.scanned_at)
    return matchesQuery && matchesDate
  })
</script>

<div class="space-y-8">
  <!-- Header -->
  <div>
    <h2 class="text-xl font-bold mb-2">History</h2>
    <p class="text-[13px] text-text-secondary">
      View your processing runs, scans, and statistics
    </p>
  </div>

  {#if loading}
    <!-- Loading State -->
    <div class="space-y-6">
      <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        {#each Array(5) as _}
          <div class="rounded-lg border border-border bg-card p-5 space-y-3">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-6 w-16" />
          </div>
        {/each}
      </div>
      <div class="rounded-lg border border-border bg-card p-6 space-y-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  {:else if error}
    <!-- Error State -->
    <div class="bg-red-500/5 border border-red-500/20 rounded-xl p-6">
      <p class="text-[13px] text-red-300">{error}</p>
      <button
        on:click={loadData}
        class="mt-4 px-4 py-2 text-[13px] text-red-300 hover:text-white transition-colors"
      >
        Retry
      </button>
    </div>
  {:else}
    <!-- Content -->
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
      <div class="rounded-xl border border-border bg-card p-5">
        <div class="text-[11px] uppercase tracking-[0.2em] text-text-tertiary mb-2">Runs</div>
        <div class="text-2xl font-semibold">{summary.totalRuns}</div>
        <div class="text-[12px] text-text-secondary">Total processing runs</div>
      </div>
      <div class="rounded-xl border border-border bg-card p-5">
        <div class="text-[11px] uppercase tracking-[0.2em] text-text-tertiary mb-2">Completed</div>
        <div class="text-2xl font-semibold text-green-300">{summary.completedRuns}</div>
        <div class="text-[12px] text-text-secondary">Runs completed</div>
      </div>
      <div class="rounded-xl border border-border bg-card p-5">
        <div class="text-[11px] uppercase tracking-[0.2em] text-text-tertiary mb-2">Files</div>
        <div class="text-2xl font-semibold">{summary.totalFiles}</div>
        <div class="text-[12px] text-text-secondary">Files processed</div>
      </div>
      <div class="rounded-xl border border-border bg-card p-5">
        <div class="text-[11px] uppercase tracking-[0.2em] text-text-tertiary mb-2">Success</div>
        <div class="text-2xl font-semibold text-green-300">{summary.successfulFiles}</div>
        <div class="text-[12px] text-text-secondary">Successful files</div>
      </div>
      <div class="rounded-xl border border-border bg-card p-5">
        <div class="text-[11px] uppercase tracking-[0.2em] text-text-tertiary mb-2">Success rate</div>
        <div class="text-2xl font-semibold">{successRate}%</div>
        <div class="text-[12px] text-text-secondary">Across all runs</div>
      </div>
    </div>

    <div class="rounded-xl border border-border bg-card p-4">
      <div class="grid gap-3 sm:grid-cols-[1.2fr,200px,200px,auto] items-end">
        <div class="space-y-1">
          <label class="text-[11px] uppercase tracking-[0.2em] text-text-tertiary">Search</label>
          <Input
            type="text"
            bind:value={query}
            placeholder="Search runs or directories"
            className="h-9 text-[12px]"
          />
        </div>
        <div class="space-y-1">
          <label class="text-[11px] uppercase tracking-[0.2em] text-text-tertiary">Status</label>
          <Combobox
            items={statusOptions}
            value={statusFilter}
            placeholder="All statuses"
            className="h-9"
            on:change={(event) => (statusFilter = event.detail.value)}
          />
        </div>
        <div class="space-y-1">
          <label class="text-[11px] uppercase tracking-[0.2em] text-text-tertiary">Date range</label>
          <div class="grid grid-cols-2 gap-2">
            <Input type="date" bind:value={dateFrom} className="h-9 text-[12px]" />
            <Input type="date" bind:value={dateTo} className="h-9 text-[12px]" />
          </div>
          <div class="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="ghost"
              className="h-8 px-2 text-[11px] text-text-secondary"
              on:click={() => applyDatePreset(7)}
            >
              Last 7 days
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 px-2 text-[11px] text-text-secondary"
              on:click={() => applyDatePreset(30)}
            >
              Last 30 days
            </Button>
          </div>
        </div>
        <div class="flex gap-2 sm:justify-end">
          <Button
            size="sm"
            variant="outline"
            className="h-9 text-[12px]"
            on:click={() => {
              query = ''
              statusFilter = 'all'
              dateFrom = ''
              dateTo = ''
            }}
          >
            Reset
          </Button>
        </div>
      </div>
    </div>

    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-sm font-semibold">Processing Runs</h3>
          <p class="text-[12px] text-text-tertiary">Recent subtitle enrichment runs</p>
        </div>
      </div>

      {#if filteredProcessingRuns.length === 0}
        <div class="border border-border rounded-xl p-10 text-center">
          <div class="flex flex-col items-center gap-4">
            <ClipboardList class="w-12 h-12 text-text-tertiary" />
            <div>
              <p class="text-[13px] text-text-secondary mb-1">No processing runs yet</p>
              <p class="text-[11px] text-text-tertiary">Process some files to see them here</p>
            </div>
          </div>
        </div>
      {:else}
        <div class="rounded-lg border border-border bg-card overflow-hidden">
          <div class="overflow-x-auto">
            <Table className="w-full">
              <TableHeader className="bg-muted/60 border-b border-border">
                <TableRow className="uppercase tracking-wider">
                  <TableHead>Run ID</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Total Files</TableHead>
                  <TableHead>Successful</TableHead>
                  <TableHead>Failed</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {#each filteredProcessingRuns as run}
                  <TableRow>
                    <TableCell>
                      <span class="text-sm font-mono">#{run.id}</span>
                    </TableCell>
                    <TableCell>
                      <span class="text-[13px] text-text-secondary">{formatDate(run.started_at)}</span>
                    </TableCell>
                    <TableCell>
                      <span class="text-[13px] text-text-secondary">{formatDate(run.completed_at)}</span>
                    </TableCell>
                    <TableCell>
                      <span class="text-[13px] text-text-secondary">{formatDuration(run.duration_seconds)}</span>
                    </TableCell>
                    <TableCell>
                      <span class="text-sm font-medium">{run.total_files}</span>
                    </TableCell>
                    <TableCell>
                      <span class="text-sm text-green-300">{run.successful_files}</span>
                    </TableCell>
                    <TableCell>
                      <span class="text-sm text-red-300">{run.failed_files}</span>
                    </TableCell>
                    <TableCell>
                      <span class="text-xs font-medium capitalize {getStatusColor(run.status)}">
                        {run.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <button
                        on:click={() => viewRunDetails(run.id)}
                        class="px-3 py-1.5 text-xs text-accent hover:text-foreground border border-accent/30 hover:border-accent rounded-md transition-colors"
                      >
                        View Details
                      </button>
                    </TableCell>
                  </TableRow>
                {/each}
              </TableBody>
            </Table>
          </div>
        </div>
      {/if}
    </div>

    <div class="space-y-4">
      <div>
        <h3 class="text-sm font-semibold">Scan History</h3>
        <p class="text-[12px] text-text-tertiary">Recent directory scans and counts</p>
      </div>

      {#if filteredScanHistory.length === 0}
        <div class="border border-border rounded-xl p-10 text-center">
          <div class="flex flex-col items-center gap-4">
            <Search class="w-12 h-12 text-text-tertiary" />
            <div>
              <p class="text-[13px] text-text-secondary mb-1">No scans yet</p>
              <p class="text-[11px] text-text-tertiary">Scan a directory to see history here</p>
            </div>
          </div>
        </div>
      {:else}
        <div class="rounded-lg border border-border bg-card overflow-hidden">
          <div class="overflow-x-auto">
            <Table className="w-full">
              <TableHeader className="bg-muted/60 border-b border-border">
                <TableRow className="uppercase tracking-wider">
                  <TableHead>Scan ID</TableHead>
                  <TableHead>Directory</TableHead>
                  <TableHead>Scanned At</TableHead>
                  <TableHead>Files Found</TableHead>
                  <TableHead>With Plot</TableHead>
                  <TableHead>Duration</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {#each filteredScanHistory as scan}
                  <TableRow>
                    <TableCell>
                      <span class="text-sm font-mono">#{scan.id}</span>
                    </TableCell>
                    <TableCell>
                      <span class="text-[13px] font-mono text-text-secondary truncate max-w-md block" title={scan.directory}>
                        {scan.directory}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span class="text-[13px] text-text-secondary">{formatDate(scan.scanned_at)}</span>
                    </TableCell>
                    <TableCell>
                      <span class="text-sm font-medium">{scan.files_found}</span>
                    </TableCell>
                    <TableCell>
                      <span class="text-sm text-green-300">{scan.files_with_plot}</span>
                    </TableCell>
                    <TableCell>
                      <span class="text-[13px] text-text-secondary">{formatScanDuration(scan.scan_duration_ms)}</span>
                    </TableCell>
                  </TableRow>
                {/each}
              </TableBody>
            </Table>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Run Details Modal -->
{#if showRunDetails}
  <div
    class="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4"
    on:click={closeRunDetails}
    role="button"
    tabindex="-1"
    on:keydown={(e) => e.key === 'Escape' && closeRunDetails()}
  >
    <div
      class="bg-bg-card border border-border rounded-2xl p-8 max-w-5xl w-full max-h-[90vh] overflow-y-auto"
      on:click|stopPropagation
      role="dialog"
      tabindex="-1"
      on:keydown
    >
      {#if loadingDetails}
        <div class="flex items-center justify-center py-16">
          <div class="flex flex-col items-center gap-4">
            <div class="w-8 h-8 border-4 border-accent/30 border-t-accent rounded-full animate-spin"></div>
            <p class="text-sm text-text-secondary">Loading run details...</p>
          </div>
        </div>
      {:else if selectedRun}
        <div class="flex items-start justify-between mb-6">
          <div>
            <h3 class="text-lg font-medium mb-1">Run #{selectedRun.id} Details</h3>
            <p class="text-sm text-text-secondary">
              Started {formatDate(selectedRun.started_at)}
            </p>
          </div>
          <button
            on:click={closeRunDetails}
            class="text-text-secondary hover:text-white transition-colors"
          >
            <X class="w-6 h-6" />
          </button>
        </div>

        <!-- Run Summary -->
        <div class="grid grid-cols-4 gap-4 mb-6">
          <div class="bg-bg-primary rounded-lg p-4">
            <div class="text-2xl font-bold">{selectedRun.total_files}</div>
            <div class="text-[11px] text-text-secondary mt-1">Total Files</div>
          </div>
          <div class="bg-green-500/5 border border-green-500/20 rounded-lg p-4">
            <div class="text-2xl font-bold text-green-300">{selectedRun.successful_files}</div>
            <div class="text-[11px] text-text-secondary mt-1">Successful</div>
          </div>
          <div class="bg-red-500/5 border border-red-500/20 rounded-lg p-4">
            <div class="text-2xl font-bold text-red-300">{selectedRun.failed_files}</div>
            <div class="text-[11px] text-text-secondary mt-1">Failed</div>
          </div>
          <div class="bg-bg-primary rounded-lg p-4">
            <div class="text-2xl font-bold">{formatDuration(selectedRun.duration_seconds)}</div>
            <div class="text-[11px] text-text-secondary mt-1">Duration</div>
          </div>
        </div>

        <!-- File Results -->
        <div>
          <h4 class="text-sm font-medium mb-3">File Results</h4>
          <div class="border border-border rounded-xl divide-y divide-border max-h-96 overflow-y-auto">
            {#each selectedRun.file_results as result}
              <div class="px-5 py-4 {result.success ? 'bg-green-500/5' : 'bg-red-500/5'}">
                <div class="flex items-start justify-between gap-4">
                  <div class="flex-1 min-w-0">
                    <div class="text-[13px] font-medium truncate" title={result.file_name}>
                      {result.file_name}
                    </div>
                    <div class="text-[11px] text-text-tertiary mt-1 truncate" title={result.file_path}>
                      {result.file_path}
                    </div>
                    {#if result.summary}
                      <div class="text-[11px] text-text-secondary mt-2 line-clamp-2">
                        {result.summary}
                      </div>
                    {/if}
                    {#if result.error_message}
                      <div class="text-[11px] text-red-300 mt-2">
                        Error: {result.error_message}
                      </div>
                    {/if}
                  </div>
                  <div class="flex flex-col items-end gap-1">
                    <span class="text-xs font-medium {result.success ? 'text-green-300' : 'text-red-300'}">
                      {result.status}
                    </span>
                    <span class="text-[11px] text-text-tertiary">
                      {formatDate(result.processed_at)}
                    </span>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <div class="flex justify-end mt-6">
          <button
            on:click={closeRunDetails}
            class="px-5 py-2.5 bg-white hover:bg-white/90 text-black text-[13px] font-medium rounded-xl transition-all"
          >
            Close
          </button>
        </div>
      {/if}
    </div>
  </div>
{/if}
