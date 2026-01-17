<script>
  import { onMount } from 'svelte'
  import { Button } from '../lib/components/ui/button'
  import { Skeleton } from '../lib/components/ui/skeleton'
  import { Clock } from 'lucide-svelte'
  import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
  } from '../lib/components/ui/table'
  import {
    getScheduledScans,
    cancelScheduledScan
  } from '../lib/api.js'

  let scans = []
  let loading = true
  let error = null
  let refreshing = false

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

  function formatDuration(ms) {
    if (!ms && ms !== 0) return 'N/A'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  function getStatusColor(status) {
    switch (status) {
      case 'completed':
        return 'text-green-300'
      case 'running':
        return 'text-blue-300'
      case 'failed':
        return 'text-red-300'
      case 'cancelled':
        return 'text-text-tertiary'
      default:
        return 'text-text-secondary'
    }
  }

  async function loadScans({ showSpinner = true } = {}) {
    if (showSpinner) {
      loading = true
    } else {
      refreshing = true
    }
    error = null
    try {
      const response = await getScheduledScans(200)
      scans = response.scans || []
    } catch (err) {
      error = `Failed to load scheduled scans: ${err.message}`
    } finally {
      loading = false
      refreshing = false
    }
  }

  async function cancelScan(scanId) {
    error = null
    try {
      await cancelScheduledScan(scanId)
      await loadScans({ showSpinner: false })
    } catch (err) {
      error = `Failed to cancel scan: ${err.message}`
    }
  }

  onMount(async () => {
    await loadScans()
  })
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <div>
      <h2 class="text-xl font-bold">Scheduled Scans</h2>
      <p class="text-[13px] text-text-secondary">
        Track scheduled scans and review their results.
      </p>
      <p class="text-[12px] text-text-tertiary">
        Create new schedules in Settings > Scheduled Scans.
      </p>
    </div>
    <Button
      size="sm"
      variant="outline"
      className="h-8 text-[12px]"
      on:click={() => loadScans({ showSpinner: false })}
      disabled={refreshing}
    >
      {refreshing ? 'Refreshing...' : 'Refresh'}
    </Button>
  </div>

  {#if error}
    <div class="bg-red-500/5 border border-red-500/20 rounded-xl p-4">
      <p class="text-[13px] text-red-300">{error}</p>
    </div>
  {/if}

  {#if loading}
    <div class="space-y-3">
      <div class="rounded-lg border border-border bg-card p-5 space-y-3">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
      <div class="rounded-lg border border-border bg-card p-5 space-y-3">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    </div>
  {:else if scans.length === 0}
    <div class="border border-border rounded-2xl p-10 text-center">
      <div class="flex flex-col items-center gap-4">
        <Clock class="w-12 h-12 text-text-tertiary" />
        <div>
          <p class="text-[13px] text-text-secondary mb-1">No scheduled scans yet</p>
          <p class="text-[11px] text-text-tertiary">Schedule a scan to see it here</p>
        </div>
      </div>
    </div>
  {:else}
    <div class="rounded-lg border border-border bg-card overflow-hidden">
      <div class="overflow-x-auto">
        <Table className="w-full">
          <TableHeader className="bg-muted/60 border-b border-border">
            <TableRow className="uppercase tracking-wider">
              <TableHead>ID</TableHead>
              <TableHead>Directory</TableHead>
              <TableHead>Scheduled</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Files Found</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {#each scans as scan}
              <TableRow>
                <TableCell>
                  <span class="text-sm font-mono">#{scan.id}</span>
                </TableCell>
                <TableCell>
                  <span
                    class="text-[13px] font-mono text-text-secondary truncate max-w-md block"
                    title={scan.directory}
                  >
                    {scan.directory}
                  </span>
                </TableCell>
                <TableCell>
                  <span class="text-[13px] text-text-secondary">{formatDate(scan.scheduled_for)}</span>
                </TableCell>
                <TableCell>
                  <span class="text-xs font-medium capitalize {getStatusColor(scan.status)}">
                    {scan.status}
                  </span>
                </TableCell>
                <TableCell>
                  <span class="text-sm font-medium">{scan.files_found ?? '—'}</span>
                </TableCell>
                <TableCell>
                  <span class="text-[13px] text-text-secondary">{formatDuration(scan.scan_duration_ms)}</span>
                </TableCell>
                <TableCell className="text-right">
                  {#if scan.status === 'scheduled'}
                    <button
                      on:click={() => cancelScan(scan.id)}
                      class="px-3 py-1.5 text-xs text-red-300 hover:text-white border border-red-400/40 hover:border-red-400 rounded-md transition-colors"
                    >
                      Cancel
                    </button>
                  {:else if scan.status === 'failed'}
                    <span class="text-[11px] text-red-300" title={scan.error_message || ''}>
                      Failed
                    </span>
                  {:else}
                    <span class="text-[11px] text-text-tertiary">—</span>
                  {/if}
                </TableCell>
              </TableRow>
            {/each}
          </TableBody>
        </Table>
      </div>
    </div>
  {/if}
</div>
