/**
 * API helper module - centralized API endpoint definitions and fetch wrappers
 * Maps to backend endpoints defined in backend/api.py
 */

const API_BASE = '/api'

/**
 * Generic fetch wrapper with error handling
 */
async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`

  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    })

    // Check if response has content
    const contentType = response.headers.get('content-type')
    if (!contentType || !contentType.includes('application/json')) {
      const text = await response.text()
      console.error(`Non-JSON response [${endpoint}]:`, text)
      throw new Error(`Server returned non-JSON response: ${text.substring(0, 100)}`)
    }

    // Get response text first to help debug parse errors
    const text = await response.text()

    // Try to parse JSON
    let data
    try {
      data = JSON.parse(text)
    } catch (parseError) {
      console.error(`JSON Parse Error [${endpoint}]:`, parseError)
      console.error('Response text:', text.substring(0, 500))
      throw new Error(`Invalid JSON response: ${parseError.message}`)
    }

    if (!response.ok) {
      throw new Error(data.error || `HTTP ${response.status}`)
    }

    return data
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error)
    throw error
  }
}

// ============ SETTINGS API ============

/**
 * GET /api/settings - Fetch current settings
 * Returns: { api_key, default_directory, cleaning_patterns, duration }
 */
export async function getSettings() {
  return apiFetch('/settings')
}

/**
 * POST /api/settings - Update settings
 * Body: { api_key?, default_directory?, duration? }
 * Returns: { success, message }
 */
export async function updateSettings(settings) {
  return apiFetch('/settings', {
    method: 'POST',
    body: JSON.stringify(settings)
  })
}

// ============ FOLDER RULES API ============

/**
 * GET /api/folder-rules - Fetch folder rules
 * Returns: { success, rules: [...] }
 */
export async function getFolderRules() {
  return apiFetch('/folder-rules')
}

/**
 * POST /api/folder-rules - Create or update a folder rule
 * Body: { directory, preferred_source?, insertion_position?, language?, subtitle_*? }
 * Returns: { success }
 */
export async function saveFolderRule(rule) {
  return apiFetch('/folder-rules', {
    method: 'POST',
    body: JSON.stringify(rule)
  })
}

/**
 * DELETE /api/folder-rules/<directory> - Delete a folder rule
 * Returns: { success }
 */
export async function deleteFolderRule(directory) {
  return apiFetch(`/folder-rules/${encodeURIComponent(directory)}`, {
    method: 'DELETE'
  })
}

// ============ SCAN API ============

/**
 * POST /api/scan/start - Start directory scan
 * Body: { directory }
 * Returns: { success, count, files: [{path, name, has_plot, status, summary, selected}] }
 */
export async function startScan(directory) {
  return apiFetch('/scan/start', {
    method: 'POST',
    body: JSON.stringify({ directory })
  })
}

/**
 * POST /api/scan/stream - Start streaming directory scan with progress updates
 * Body: { directory }
 * Returns: EventSource stream with progress updates
 *
 * Usage:
 *   streamScan(directory, {
 *     onProgress: (data) => { console.log('Progress:', data.filesFound) },
 *     onComplete: (data) => { console.log('Done:', data.files) },
 *     onError: (error) => { console.error('Error:', error) }
 *   })
 */
export async function streamScan(directory, callbacks = {}, abortSignal = null) {
  const { onProgress, onComplete, onError, onStatus } = callbacks

  return new Promise((resolve, reject) => {
    // Use fetch to POST the directory, then read the stream
    fetch(`${API_BASE}/scan/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ directory }),
      signal: abortSignal
    })
      .then(async response => {
        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.error || `HTTP ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        // Read the stream
        const processStream = async () => {
          let lastCompleteData = null

          try {
            while (true) {
              const { done, value } = await reader.read()

              if (done) {
                // Stream ended naturally - check if we got a complete message
                console.log('Stream ended. lastCompleteData:', !!lastCompleteData)
                if (lastCompleteData) {
                  console.log('Calling onComplete with data:', lastCompleteData)
                  onComplete && onComplete(lastCompleteData)
                  resolve(lastCompleteData)
                } else {
                  // Stream ended without complete message - this shouldn't happen
                  console.error('Stream ended without receiving complete message from backend')
                  const error = new Error('Stream ended unexpectedly without completion message')
                  onError && onError(error)
                  reject(error)
                }
                return
              }

              // Decode chunk and add to buffer
              buffer += decoder.decode(value, { stream: true })

              // Process complete messages (SSE format: "data: {...}\n\n")
              const lines = buffer.split('\n\n')
              buffer = lines.pop() // Keep incomplete message in buffer

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.slice(6))

                    switch (data.type) {
                      case 'status':
                        onStatus && onStatus(data)
                        break
                      case 'progress':
                        onProgress && onProgress(data)
                        break
                      case 'complete':
                        // Store complete data but don't resolve yet - wait for stream to end
                        console.log('Received complete message from backend:', data)
                        lastCompleteData = data
                        break
                      case 'error':
                        const error = new Error(data.error || 'Scan failed')
                        onError && onError(error)
                        reject(error)
                        return
                    }
                  } catch (parseError) {
                    console.error('Failed to parse SSE message:', line, parseError)
                  }
                }
              }
            }
          } catch (streamError) {
            console.error('Stream reading error:', streamError)
            onError && onError(streamError)
            reject(streamError)
          }
        }

        await processStream()
      })
      .catch(error => {
        console.error('Stream scan error:', error)
        onError && onError(error)
        reject(error)
      })
  })
}

/**
 * GET /api/scan/status - Get scan status and results
 * Returns: { scanning, last_scan, file_count, files }
 */
export async function getScanStatus() {
  return apiFetch('/scan/status')
}

// ============ SEARCH API ============

/**
 * POST /api/search - Search for title matches
 * Body: { query: string, mode?: "quick" | "full" }
 * - "quick" (default): Returns single best match (1 API call) - good for auto-matching
 * - "full": Returns multiple results to choose from (2 API calls) - good for manual search
 * Returns: { success, results: [{title, year, plot, runtime, imdb_rating, media_type, poster, imdb_id}] }
 */
export async function searchTitle(query, mode = "quick", options = {}) {
  const body = { query, mode }
  if (options.preferredSource) {
    body.preferred_source = options.preferredSource
  }
  if (options.language) {
    body.language = options.language
  }
  return apiFetch('/search', {
    method: 'POST',
    body: JSON.stringify(body)
  })
}

// ============ PROCESSING API ============

/**
 * POST /api/process - Process files to add plot summaries
 * Body: { files: [string], duration: number, titleOverride?: object, forceReprocess?: boolean }
 * Returns: { success, results: [{file, success, status, summary, error?}] }
 */
export async function processFiles(files, duration, titleOverride = null, forceReprocess = false) {
  const body = { files, duration }

  if (titleOverride) {
    body.titleOverride = titleOverride
  }

  if (forceReprocess) {
    body.forceReprocess = forceReprocess
  }

  return apiFetch('/process', {
    method: 'POST',
    body: JSON.stringify(body)
  })
}

// ============ UTILITY API ============

/**
 * GET /api/health - Health check
 * Returns: { status, api_key_configured }
 */
export async function healthCheck() {
  return apiFetch('/health')
}

// ============ HISTORY API ============

/**
 * GET /api/history/runs - Get processing run history
 * Returns: { success, runs: [{id, started_at, completed_at, total_files, successful_files, failed_files, duration_seconds, status}] }
 */
export async function getRunHistory(limit = 50) {
  return apiFetch(`/history/runs?limit=${limit}`)
}

/**
 * GET /api/history/runs/<id> - Get detailed run information
 * Returns: { success, run: {id, started_at, completed_at, file_results: [...]} }
 */
export async function getRunDetails(runId) {
  return apiFetch(`/history/runs/${runId}`)
}

/**
 * GET /api/history/scans - Get scan history
 * Returns: { success, scans: [{id, directory, scanned_at, files_found, files_with_plot, scan_duration_ms}] }
 */
export async function getScanHistory(limit = 50) {
  return apiFetch(`/history/scans?limit=${limit}`)
}

/**
 * GET /api/statistics - Get overall statistics
 * Returns: { success, statistics: {total_runs, completed_runs, total_files_processed, successful_files, failed_files} }
 */
export async function getStatistics() {
  return apiFetch('/statistics')
}

// ============ LIBRARY API ============

/**
 * GET /api/library - Get library health report
 * Returns: { success, items: [...], total_items, page, page_size, has_more }
 */
export async function getLibraryReport(page = 1, pageSize = 200) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize)
  })
  return apiFetch(`/library?${params.toString()}`)
}

// ============ SCHEDULED SCANS API ============

/**
 * GET /api/scheduled-scans - Get scheduled scans
 * Returns: { success, scans: [{id, directory, scheduled_for, status, files_found, files_with_plot, scan_duration_ms}] }
 */
export async function getScheduledScans(limit = 50, status = null) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (status) {
    params.append('status', status)
  }
  return apiFetch(`/scheduled-scans?${params.toString()}`)
}

/**
 * POST /api/scheduled-scans - Create a scheduled scan
 * Body: { directory, scheduled_for }
 * Returns: { success, id }
 */
export async function createScheduledScan(directory, scheduledFor) {
  return apiFetch('/scheduled-scans', {
    method: 'POST',
    body: JSON.stringify({ directory, scheduled_for: scheduledFor })
  })
}

/**
 * POST /api/scheduled-scans/<id>/cancel - Cancel a scheduled scan
 * Returns: { success }
 */
export async function cancelScheduledScan(scanId) {
  return apiFetch(`/scheduled-scans/${scanId}/cancel`, {
    method: 'POST'
  })
}

// ============ INTEGRATIONS API ============

/**
 * GET /api/integrations/usage - Get API usage statistics
 * Returns: { success, usage: { omdb: {...}, tmdb: {...}, tvmaze: {...} } }
 */
export async function getIntegrationUsage() {
  return apiFetch('/integrations/usage')
}

// ============ SUGGESTED MATCHES API ============

/**
 * POST /api/suggested-matches - Save suggested matches
 * Body: { matches: { filePath: matchData } }
 * Returns: { success, count }
 */
export async function saveSuggestedMatches(matches) {
  return apiFetch('/suggested-matches', {
    method: 'POST',
    body: JSON.stringify({ matches })
  })
}

/**
 * DELETE /api/suggested-matches/<file_path> - Delete a suggested match
 * Returns: { success }
 */
export async function deleteSuggestedMatch(filePath) {
  return apiFetch(`/suggested-matches/${encodeURIComponent(filePath)}`, {
    method: 'DELETE'
  })
}

/**
 * DELETE /api/suggested-matches - Clear all suggested matches
 * Returns: { success }
 */
export async function clearAllSuggestedMatches() {
  return apiFetch('/suggested-matches', {
    method: 'DELETE'
  })
}

// ============ MAINTENANCE API ============

/**
 * POST /api/maintenance/reset-settings - Clear settings, optionally keeping API keys
 * Body: { keep_api_keys: boolean }
 * Returns: { success }
 */
export async function resetSettings(keepApiKeys = false) {
  return apiFetch('/maintenance/reset-settings', {
    method: 'POST',
    body: JSON.stringify({ keep_api_keys: keepApiKeys })
  })
}

/**
 * POST /api/maintenance/clear-history - Clear runs, scans, scheduled scans, and usage logs
 * Returns: { success }
 */
export async function clearHistory() {
  return apiFetch('/maintenance/clear-history', {
    method: 'POST'
  })
}

/**
 * POST /api/maintenance/clear-caches - Clear cached data like suggested matches
 * Returns: { success }
 */
export async function clearCaches() {
  return apiFetch('/maintenance/clear-caches', {
    method: 'POST'
  })
}

// ============ BATCH PROCESSING API ============

/**
 * POST /api/process/batch - Process multiple files with SSE streaming progress
 * Body: { items: [{ path, titleOverride }], duration? }
 * Returns: SSE stream with progress updates
 *
 * Usage:
 *   processBatch(items, duration, {
 *     onStart: (data) => { console.log('Starting:', data.total) },
 *     onProgress: (data) => { console.log('Progress:', data.current, '/', data.total) },
 *     onResult: (data) => { console.log('Result:', data.file, data.success) },
 *     onComplete: (data) => { console.log('Done:', data.successful, '/', data.total) },
 *     onError: (error) => { console.error('Error:', error) }
 *   })
 */
export async function processBatch(items, duration, callbacks = {}) {
  const { onStart, onProgress, onResult, onComplete, onError } = callbacks

  return new Promise((resolve, reject) => {
    fetch(`${API_BASE}/process/batch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ items, duration })
    })
      .then(async response => {
        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.error || `HTTP ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        let lastCompleteData = null

        const processStream = async () => {
          try {
            while (true) {
              const { done, value } = await reader.read()

              if (done) {
                if (lastCompleteData) {
                  onComplete && onComplete(lastCompleteData)
                  resolve(lastCompleteData)
                } else {
                  const error = new Error('Stream ended unexpectedly')
                  onError && onError(error)
                  reject(error)
                }
                return
              }

              buffer += decoder.decode(value, { stream: true })

              const lines = buffer.split('\n\n')
              buffer = lines.pop()

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.slice(6))

                    switch (data.type) {
                      case 'start':
                        onStart && onStart(data)
                        break
                      case 'progress':
                        onProgress && onProgress(data)
                        break
                      case 'result':
                        onResult && onResult(data)
                        break
                      case 'complete':
                        lastCompleteData = data
                        break
                      case 'error':
                        const error = new Error(data.error || 'Processing failed')
                        onError && onError(error)
                        reject(error)
                        return
                    }
                  } catch (parseError) {
                    console.error('Failed to parse SSE message:', line, parseError)
                  }
                }
              }
            }
          } catch (streamError) {
            console.error('Stream reading error:', streamError)
            onError && onError(streamError)
            reject(streamError)
          }
        }

        await processStream()
      })
      .catch(error => {
        console.error('Batch processing error:', error)
        onError && onError(error)
        reject(error)
      })
  })
}
