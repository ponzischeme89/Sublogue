<script>
  import { onMount, tick } from "svelte";
  import {
    streamScan,
    getSettings,
    updateSettings,
    processFiles,
    clearAllSuggestedMatches,
    getFolderRules,
    getScanHistory,
  } from "../lib/api.js";
  import ResultsList from "./ResultsList.svelte";
  import TypewriterQuote from "./TypewriterQuote.svelte";
  import { scanResults } from "../lib/scanStore.js";
  import { Button } from "../lib/components/ui/button";
  import { addToast } from "../lib/toastStore.js";
  import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
  } from "../lib/components/ui/card";
  import { Input } from "../lib/components/ui/input";
  import { Skeleton } from "../lib/components/ui/skeleton";
  import { Combobox } from "../lib/components/ui/combobox";
  import { FileText, Folder, Info, Plug, Scan } from "lucide-svelte";

  // ------------------------------------------------------------
  // clickOutside action (pure Svelte)
  // - Closes when clicking outside node
  // - Closes on Escape
  // - Cleans up listeners on destroy
  // ------------------------------------------------------------
  function clickOutside(node, handler) {
    if (typeof handler !== "function") return { destroy() {} };

    const onPointerDown = (event) => {
      // If click is outside the node, close
      if (!node.contains(event.target)) handler(event);
    };

    const onKeyDown = (event) => {
      if (event.key === "Escape") handler(event);
    };

    // Capture phase makes this reliable even if inner elements stopPropagation
    document.addEventListener("mousedown", onPointerDown, true);
    document.addEventListener("touchstart", onPointerDown, true);
    document.addEventListener("keydown", onKeyDown, true);

    return {
      destroy() {
        document.removeEventListener("mousedown", onPointerDown, true);
        document.removeEventListener("touchstart", onPointerDown, true);
        document.removeEventListener("keydown", onKeyDown, true);
      },
    };
  }

  let directory = "";
  let files = [];
  let scanning = false;
  let error = null;
  let lastScan = null;
  let selectedFilePaths = [];
  let metadataProvider = "omdb";
  let metadataLanguage = "";
  let omdbEnabled = false;
  let tmdbEnabled = false;
  let tvmazeEnabled = false;
  let settingsLoaded = false;
  let defaultDirectory = "";
  let showSaveDirectoryPrompt = false;
  let savingDirectory = false;
  let processing = false;
  let duration = 40;
  let processingResults = null;
  let showConfirmation = false;
  let pendingProcessFiles = [];
  let pendingTitleOverride = null;
  let resultsListRef = null;
  let pendingForceReprocess = false;
  let quoteStyle = 'sarcastic';
  let initialLoading = true;
  let scanToastedError = false;
  let metadataOptions = [];
  let activeMetadataOptions = [];
  $: metadataOptions = [
    {
      value: "omdb",
      label: "OMDb",
      description: "Open Movie Database",
      disabled: !omdbEnabled,
    },
    {
      value: "tmdb",
      label: "TMDb",
      description: "The Movie Database",
      disabled: !tmdbEnabled,
    },
    {
      value: "tvmaze",
      label: "TVmaze",
      description: "TV metadata without an API key",
      disabled: !tvmazeEnabled,
    },
    {
      value: "both",
      label: "Both",
      description: "OMDb + TMDb fallback",
      disabled: !(omdbEnabled && tmdbEnabled),
    },
  ];
  $: activeMetadataOptions = metadataOptions.filter((opt) => !opt.disabled);

  // Scan progress tracking
  let scanProgress = {
    filesFound: 0,
    message: "",
    scanning: false,
    startedAt: null,
    estimatedFinishAt: null,
  };
  let scanHistory = [];
  let expectedTotalFiles = null;

  // Scan cancellation
  let scanAbortController = null;

  export let apiConfigured = false;
  export let onOpenSettings = null;
  export let onOpenHistory = null;
  export { selectedFilePaths, metadataProvider };
  let onboardingComplete = false;
  let hasScannedBefore = false;
  let folderRules = [];
  let activeFolderRule = null;

  onMount(async () => {
    const initialTimer = setTimeout(() => {
      initialLoading = false;
    }, 500);
    try {
      const settings = await getSettings();
      directory = settings.default_directory || "";
      defaultDirectory = settings.default_directory || "";
      metadataProvider = settings.preferred_source || "omdb";
      quoteStyle = settings.quote_style || "sarcastic";
      omdbEnabled = settings.omdb_enabled ?? false;
      tmdbEnabled = settings.tmdb_enabled ?? false;
      tvmazeEnabled = settings.tvmaze_enabled ?? false;
      settingsLoaded = true;

      // Load previous scan results from store if available
      const storedResults = $scanResults;
      if (storedResults.files.length > 0) {
        files = storedResults.files;
        lastScan = storedResults.lastScan;
        directory = storedResults.directory || directory;
      }
      if (typeof localStorage !== "undefined") {
        onboardingComplete =
          localStorage.getItem("sublogue_onboarding_complete") === "true";
        hasScannedBefore =
          localStorage.getItem("sublogue_has_scanned") === "true";
      }
      try {
        const rulesResponse = await getFolderRules();
        folderRules = rulesResponse.rules || [];
      } catch (err) {
        console.error("Failed to load folder rules:", err);
      }
      try {
        const historyResponse = await getScanHistory(10);
        scanHistory = historyResponse.scans || [];
      } catch (err) {
        console.error("Failed to load scan history:", err);
      }
    } catch (err) {
      console.error("Failed to load initial data:", err);
    }
    return () => clearTimeout(initialTimer);
  });

  async function handleScan() {
    if (!directory) {
      error = "Please enter a directory path";
      addToast({ message: "Please enter a directory path.", tone: "error" });
      return;
    }

    // Check if directory is different from default
    const isDifferentDirectory =
      directory !== defaultDirectory && directory.trim() !== "";

    scanning = true;
    error = null;
    scanToastedError = false;
    scanProgress = {
      filesFound: 0,
      message: "Starting scan...",
      scanning: true,
      startedAt: new Date(),
      estimatedFinishAt: null,
    };
    expectedTotalFiles = null;
    if (scanHistory.length > 0 && directory) {
      const normalizedDir = directory.toLowerCase();
      const lastMatch = scanHistory.find(
        (scan) => (scan.directory || "").toLowerCase() === normalizedDir,
      );
      if (lastMatch && lastMatch.files_found) {
        expectedTotalFiles = lastMatch.files_found;
      }
    }
    addToast({ message: "Scan started.", tone: "info" });

    // Reset files array before starting new scan
    files = [];

    // Create new abort controller for this scan
    scanAbortController = new AbortController();

    try {
      // Use streaming scan for real-time progress
      await streamScan(
        directory,
        {
          onStatus: (data) => {
            console.log("Stream onStatus:", data);
            scanProgress = {
              ...scanProgress,
              message: data.message,
              filesFound: data.filesFound,
            };
          },
          onProgress: async (data) => {
            console.log("Stream onProgress:", data.filesFound, "files");
            scanProgress = {
              ...scanProgress,
              message: data.message,
              filesFound: data.filesFound,
            };
            if (
              scanProgress.startedAt &&
              expectedTotalFiles &&
              data.filesFound > 0
            ) {
              const elapsedMs =
                new Date().getTime() - scanProgress.startedAt.getTime();
              const estimatedTotalMs =
                (elapsedMs * expectedTotalFiles) / data.filesFound;
              const estimatedFinish = new Date(
                scanProgress.startedAt.getTime() + estimatedTotalMs,
              );
              scanProgress = {
                ...scanProgress,
                estimatedFinishAt: estimatedFinish,
              };
            }

            // Incrementally add files as they're found
            const previousLength = files.length;
            files = [...files, ...data.batch];

            // Trigger auto-matching for the new batch if ResultsList is ready
            if (resultsListRef && data.batch && data.batch.length > 0) {
              console.log(
                "Auto-matching new batch of",
                data.batch.length,
                "files",
              );
              // Auto-match only the new files that were just added
              await resultsListRef.autoMatchBatch(data.batch);
            }
          },
          onComplete: async (data) => {
            console.log("🎯 ONCOMPLETE CALLED!", data);
            // Use the accumulated files from progress updates
            // Only replace if we somehow have fewer files (shouldn't happen)
            if (data.files && data.files.length > files.length) {
              files = data.files;
            }

            lastScan = new Date().toISOString();
            if (data.count != null) {
              expectedTotalFiles = data.count;
            }

            // Save to store
            scanResults.setScanResults(files, directory);
            if (typeof localStorage !== "undefined") {
              localStorage.setItem("sublogue_has_scanned", "true");
              hasScannedBefore = true;
            }

            // Show save prompt if scanning a new directory
            if (isDifferentDirectory) {
              showSaveDirectoryPrompt = true;
            }

            // DON'T force re-render with key change - it destroys the component reference
            // Instead, just let Svelte's reactivity update the ResultsList
            await tick();

            // Wait a bit longer for the component to be ready
            await new Promise((resolve) => setTimeout(resolve, 100));

            // Load existing suggested matches first (if available)
            const existingMatches = data.suggested_matches || {};

            if (files.length > 0) {
              console.log("=== Starting auto-match process ===");
              console.log("Files:", files.length);
              console.log("ResultsListRef exists:", !!resultsListRef);
              console.log(
                "Existing matches:",
                Object.keys(existingMatches).length,
              );

              if (resultsListRef) {
                // ALWAYS load existing matches from database first (even if empty, to reset state)
                console.log(
                  "Loading existing matches into component:",
                  Object.keys(existingMatches).length,
                );
                resultsListRef.loadSuggestedMatches(existingMatches);
                await tick();

                // Small delay to ensure state is fully propagated
                await new Promise((resolve) => setTimeout(resolve, 50));

                // Now run auto-match - it will skip files that already have matches
                console.log(
                  "Starting autoMatchAll with",
                  files.length,
                  "files...",
                );
                console.log(
                  "suggestedMatches should have",
                  Object.keys(existingMatches).length,
                  "entries",
                );
                await resultsListRef.autoMatchAll();
                console.log("autoMatchAll completed successfully");
              } else {
                console.error(
                  "ERROR: resultsListRef is null! Cannot run auto-match.",
                );
              }
            }
            addToast({
              message: `Scan complete. ${data.count ?? files.length} files found.`,
              tone: "success",
            });
          },
          onError: (err) => {
            console.log("🚨 ONERROR CALLED!", err);
            if (err.name === "AbortError") {
              error = "Scan cancelled by user";
            } else {
              error = `Scan failed: ${err.message}`;
            }
            scanToastedError = true;
            addToast({
              message: err.name === "AbortError" ? "Scan cancelled." : "Scan failed.",
              tone: err.name === "AbortError" ? "info" : "error",
            });
          },
        },
        scanAbortController.signal,
      );
    } catch (err) {
      if (err.name === "AbortError") {
        error = "Scan cancelled by user";
      } else {
        error = `Scan failed: ${err.message}`;
      }
      if (!scanToastedError) {
        addToast({
          message: err.name === "AbortError" ? "Scan cancelled." : "Scan failed.",
          tone: err.name === "AbortError" ? "info" : "error",
        });
      }
    } finally {
      scanning = false;
      scanProgress.scanning = false;
      scanProgress.estimatedFinishAt = null;
      scanAbortController = null;
    }
  }

  function cancelScan() {
    if (scanAbortController) {
      scanAbortController.abort();
      scanAbortController = null;
      scanning = false;
      scanProgress.scanning = false;
      error = "Scan cancelled";
      addToast({ message: "Scan cancelled.", tone: "info" });
    }
  }

  function handleSelectionChange(selected) {
    selectedFilePaths = selected;
  }

  async function clearResults() {
    // Reset ALL local state variables
    files = [];
    selectedFilePaths = [];
    lastScan = null;
    error = null;
    processingResults = null;
    showConfirmation = false;
    pendingProcessFiles = [];
    pendingTitleOverride = null;
    showSaveDirectoryPrompt = false;

    // Clear Svelte store
    scanResults.clearResults();

    // Clear ResultsList component state
    if (resultsListRef) {
      resultsListRef.clearMatchingState();
    }

    // CRITICAL: Clear backend state (database + in-memory)
    try {
      await clearAllSuggestedMatches();
      console.log("Successfully cleared all backend state");
    } catch (err) {
      console.error("Failed to clear backend state:", err);
      error = "Failed to clear results completely. Please try again.";
    }
  }

  async function saveAsDefaultDirectory() {
    savingDirectory = true;
    try {
      await updateSettings({ default_directory: directory });
      defaultDirectory = directory;
      showSaveDirectoryPrompt = false;
    } catch (err) {
      console.error("Failed to save default directory:", err);
      error = "Failed to save directory setting";
    } finally {
      savingDirectory = false;
    }
  }

  function dismissDirectoryPrompt() {
    showSaveDirectoryPrompt = false;
  }

  async function handleProcessSingle(event) {
    pendingProcessFiles = event.detail.files;
    pendingTitleOverride = event.detail.titleOverride || null;
    pendingForceReprocess = event.detail.forceReprocess || false;
    await prepareProcessing();
  }

  async function handleProcessBulk(event) {
    pendingProcessFiles = event.detail.files;
    pendingTitleOverride = null; // Bulk processing doesn't support title override
    await prepareProcessing();
  }

  async function prepareProcessing() {
    if (pendingProcessFiles.length === 0) return;

    try {
      const settings = await getSettings();
      duration = settings.duration ?? 40;
    } catch (err) {
      console.error("Failed to load duration:", err);
    }

    showConfirmation = true;
  }

  async function confirmProcess() {
    processing = true;
    showConfirmation = false;
    error = null;
    processingResults = null;

    try {
      // Pass title override if provided, and force reprocess if explicitly requested or if title override exists
      const forceReprocess = pendingForceReprocess || !!pendingTitleOverride;
      const response = await processFiles(
        pendingProcessFiles,
        duration,
        pendingTitleOverride,
        forceReprocess,
      );
      processingResults = response.results;

      // Update the files list with new status/summary
      if (processingResults) {
        files = files.map((file) => {
          const result = processingResults.find((r) => r.file === file.path);
          if (result) {
            return {
              ...file,
              status: result.status || (result.success ? "Processed" : "Error"),
              summary: result.summary || file.summary || "",
              plot: result.summary || file.plot || "",
              has_plot: result.success,
              // Add metadata from processing result
              title: result.title || file.title,
              year: result.year || file.year,
              imdb_rating: result.imdb_rating || file.imdb_rating,
              rating: result.imdb_rating || file.rating,
              runtime: result.runtime || file.runtime,
              media_type: result.media_type || file.media_type,
            };
          }
          return file;
        });
        // Update store with new file data
        scanResults.setScanResults(files, directory);
      }
    } catch (err) {
      error = `Processing failed: ${err.message}`;
    } finally {
      processing = false;
      pendingProcessFiles = [];
      pendingForceReprocess = false;
    }
  }

  function cancelProcess() {
    showConfirmation = false;
    pendingProcessFiles = [];
    pendingForceReprocess = false;
  }

  function closeResults() {
    processingResults = null;
  }

  function handleMetadataSourceChange(event) {
    metadataProvider = event.detail.source;
  }

  function normalizePath(path) {
    return (path || "")
      .replace(/\//g, "\\")
      .replace(/\\+$/, "")
      .toLowerCase();
  }

  function findFolderRuleForDirectory(path, rules) {
    const target = normalizePath(path);
    if (!target) return null;
    let bestRule = null;
    let bestLength = -1;
    for (const rule of rules) {
      const dir = normalizePath(rule.directory);
      if (!dir) continue;
      if (target === dir || target.startsWith(dir + "\\")) {
        if (dir.length > bestLength) {
          bestLength = dir.length;
          bestRule = rule;
        }
      }
    }
    return bestRule;
  }

  function formatMetadataLabel(source) {
    if (source === "both") return "OMDb + TMDb";
    if (source === "tvmaze") return "TVmaze";
    return source.toUpperCase();
  }

  async function selectMetadataSource(source) {
    metadataProvider = source;

    // Save the preference to backend
    try {
      await updateSettings({ preferred_source: source });
    } catch (err) {
      console.error("Failed to save metadata source preference:", err);
    }
  }

  function resolveMetadataProvider(nextOptions) {
    if (!settingsLoaded) return;
    if (nextOptions.length === 0) {
      metadataProvider = "";
      return;
    }
    if (!nextOptions.some((opt) => opt.value === metadataProvider)) {
      const fallback = nextOptions[0].value;
      metadataProvider = fallback;
      updateSettings({ preferred_source: fallback }).catch((err) => {
        console.error("Failed to save metadata source preference:", err);
      });
    }
  }

  $: hasScanned = lastScan !== null || files.length > 0;
  $: successCount = processingResults?.filter((r) => r.success).length || 0;
  $: failureCount = processingResults?.filter((r) => !r.success).length || 0;
  $: metadataSelected = !!metadataProvider;
  $: resolveMetadataProvider(activeMetadataOptions);
  $: if (folderRules.length && directory) {
    const matchedRule = findFolderRuleForDirectory(directory, folderRules);
    activeFolderRule = matchedRule;
    if (matchedRule) {
      if (matchedRule.preferred_source) {
        metadataProvider = matchedRule.preferred_source;
      }
      metadataLanguage = matchedRule.language || "";
    } else {
      activeFolderRule = null;
      metadataLanguage = "";
    }
  }
  $: allStepsComplete = apiConfigured && metadataSelected && hasScanned;
  $: if (allStepsComplete && !onboardingComplete) {
    onboardingComplete = true;
    if (typeof localStorage !== "undefined") {
      localStorage.setItem("sublogue_onboarding_complete", "true");
    }
  }
  $: showTutorial = !onboardingComplete && !hasScanned && !hasScannedBefore;
</script>

<div class="space-y-8">
  {#if initialLoading}
    <div class="space-y-6">
      <div class="rounded-lg border border-border bg-card p-6 space-y-4">
        <Skeleton className="h-5 w-40" />
        <div class="flex gap-3">
          <Skeleton className="h-11 flex-1" />
          <Skeleton className="h-11 w-40" />
        </div>
        <div class="flex items-center gap-3">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-10 w-48" />
          <Skeleton className="h-4 w-40" />
        </div>
      </div>

      <div class="rounded-lg border border-border bg-card p-6 space-y-3">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>

      <div class="rounded-lg border border-border bg-card p-6 space-y-3">
        <Skeleton className="h-4 w-36" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  {:else}
  <!-- Scan Panel -->
  <Card className="bg-card" skeletonFlash={false}>
    <CardHeader className="pb-4">
      <CardTitle className="text-base">Scan your SRT files</CardTitle>
      <CardDescription className="text-[13px]">
        Scan folders for subtitles missing plot summaries
      </CardDescription>
    </CardHeader>

    <CardContent className="space-y-4">
      <div class="flex flex-col sm:flex-row gap-3">
        <div class="relative w-full">
          <Folder class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
          <Input
            type="text"
            bind:value={directory}
            placeholder="C:\Movies or /media/movies"
            disabled={scanning}
            className="h-11 font-mono text-[13px] w-full pl-10"
          />
        </div>
        <Button
          on:click={handleScan}
          disabled={scanning || !directory}
          size="lg"
          className="h-11 px-6 whitespace-nowrap w-full sm:w-auto"
        >
          <Scan class="h-4 w-4" />
          {scanning ? "Scanning..." : "Scan Directory"}
        </Button>
      </div>

      <div class="flex flex-col sm:flex-row sm:items-center gap-3">
        <span class="text-[13px] text-text-secondary whitespace-nowrap inline-flex items-center gap-2">
          <Plug class="h-4 w-4 text-text-tertiary" />
          Metadata Source
        </span>

        <Combobox
          items={metadataOptions}
          value={metadataProvider}
          disabled={scanning || activeMetadataOptions.length === 0}
          placeholder={
            activeMetadataOptions.length === 0
              ? "Enable a provider"
              : "Select source"
          }
          className="w-full sm:min-w-[220px]"
          on:change={(event) => selectMetadataSource(event.detail.value)}
        >
          <Plug slot="icon" class="h-4 w-4 text-text-tertiary" />
        </Combobox>

        <span class="text-[11px] text-text-tertiary sm:ml-2">
          {activeMetadataOptions.length === 0
            ? "Enable an integration in Settings to select a source."
            : "Choose which API to use for fetching plot summaries"}
        </span>
        </div>

      {#if error}
        <div class="px-5 py-4 bg-red-500/5 border border-red-500/20 rounded-xl">
          <p class="text-[13px] text-red-300">{error}</p>
        </div>
      {/if}

      {#if scanning}
        <div
          class="px-6 py-5 bg-blue-500/5 border border-blue-500/20 rounded-xl"
        >
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
            <div class="flex items-center gap-3">
              <div
                class="w-4 h-4 border-2 border-blue-500/40 border-t-blue-500 rounded-full animate-spin"
              ></div>
              <span class="text-[13px] font-medium text-blue-300"
                >{scanProgress.message}</span
              >
            </div>
            <Button
              on:click={cancelScan}
              variant="outline"
              size="sm"
              className="border-red-500/60 text-red-400 hover:bg-red-500/10 w-full sm:w-auto"
            >
              Cancel
            </Button>
          </div>

          {#if scanProgress.filesFound > 0}
            <div
              class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-[12px] text-text-secondary"
            >
              <span
                >Files found: <span class="text-white font-medium"
                  >{scanProgress.filesFound}</span
                ></span
              >
              <span class="text-text-tertiary">Scanning in progress...</span>
            </div>
            {#if scanProgress.startedAt}
              <div class="mt-2 text-[11px] text-text-tertiary">
                Started at {scanProgress.startedAt.toLocaleTimeString()}
                {#if scanProgress.estimatedFinishAt}
                  · Estimated finish {scanProgress.estimatedFinishAt.toLocaleTimeString()}
                {/if}
              </div>
            {/if}

            <!-- Progress bar -->
            <div
              class="mt-3 h-1.5 bg-bg-secondary rounded-full overflow-hidden"
            >
              <div
                class="h-full bg-blue-500 rounded-full animate-pulse"
                style="width: 100%"
              ></div>
            </div>
          {/if}
        </div>
      {/if}
    </CardContent>
  </Card>

  <!-- Save Directory Prompt -->
  {#if showSaveDirectoryPrompt}
    <div class="bg-blue-500/5 border border-blue-500/20 rounded-2xl p-6">
      <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-2">
            <Info class="w-5 h-5 text-blue-400" />
            <h3 class="text-[13px] font-medium text-blue-300">
              Save as Default Directory?
            </h3>
          </div>
          <p class="text-[11px] text-text-secondary">
            Would you like to make <span class="font-mono text-white"
              >{directory}</span
            > as your default scan directory?
          </p>
        </div>
        <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
          <Button
            on:click={dismissDirectoryPrompt}
            disabled={savingDirectory}
            variant="ghost"
            size="sm"
            className="text-text-secondary w-full sm:w-auto"
          >
            Not now
          </Button>
          <Button
            on:click={saveAsDefaultDirectory}
            disabled={savingDirectory}
            size="sm"
            className="bg-blue-500 text-white hover:bg-blue-600 w-full sm:w-auto"
          >
            {savingDirectory ? "Saving..." : "Save"}
          </Button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Results Area -->
  {#if hasScanned}
    <div class="space-y-6">
      {#if files.length > 0}
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div class="flex flex-wrap items-center gap-4">
            <h3 class="text-[13px] font-medium text-text-secondary">
              {files.length}
              {files.length !== 1 ? "files" : "file"} found
            </h3>
            <span class="text-[13px] text-text-tertiary">
              {selectedFilePaths.length} selected
            </span>
          </div>
          <Button
            on:click={clearResults}
            variant="outline"
            size="sm"
            className="border-red-500 text-red-400 hover:bg-red-500/10 hover:text-red-300 w-full sm:w-auto"
          >
            Clear Results
          </Button>
        </div>

        <ResultsList
          bind:this={resultsListRef}
          {files}
          onSelectionChange={handleSelectionChange}
          disabled={!apiConfigured || processing}
          {metadataProvider}
          {metadataLanguage}
          activeIntegrations={{
            omdb: omdbEnabled,
            tmdb: tmdbEnabled,
            tvmaze: tvmazeEnabled,
          }}
          loading={processing}
          on:processSingle={handleProcessSingle}
          on:processBulk={handleProcessBulk}
          on:metadataSourceChange={handleMetadataSourceChange}
        />
      {:else}
        <div class="border border-border rounded-2xl p-12 text-center">
          <div class="flex flex-col items-center gap-4">
            <FileText class="w-12 h-12 text-text-tertiary" />
            <div>
              <p class="text-[13px] text-text-secondary mb-1">
                No subtitle files found
              </p>
              <p class="text-[11px] text-text-tertiary">
                Try scanning a different directory
              </p>
            </div>
            <Button
              on:click={clearResults}
              variant="ghost"
              size="sm"
              className="text-text-secondary"
            >
              Clear
            </Button>
          </div>
        </div>
      {/if}
    </div>
  {:else if !scanning && showTutorial}
    <!-- First-time tutorial -->
    <div class="rounded-2xl border border-border bg-gradient-to-br from-[#101010] via-[#0c0c0c] to-[#0b0b0b] p-6 sm:p-8">
      <div class="flex flex-col gap-6 lg:flex-row lg:items-start">
        <div class="flex-1 space-y-4">
          <div class="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-text-tertiary">
            First time setup
          </div>
          <div class="space-y-2">
            <h3 class="text-lg font-semibold text-white">
              Enrich your subtitle library in minutes
            </h3>
            <p class="text-[13px] text-text-secondary">
              Follow the steps below to connect your metadata source and scan a directory.
            </p>
          </div>
          <div class="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
            <TypewriterQuote style={quoteStyle} />
            <p class="text-[11px] text-text-tertiary mt-1">
              Enter a directory path above to begin.
            </p>
          </div>
          <div class="flex flex-wrap gap-3">
            <Button
              on:click={() => onOpenSettings && onOpenSettings()}
              size="sm"
              className="bg-white text-black hover:bg-white/90"
            >
              Open Settings
            </Button>
            <Button
              on:click={() => onOpenHistory && onOpenHistory()}
              variant="outline"
              size="sm"
              className="border-white/20 text-text-secondary hover:bg-white/10"
            >
              View History
            </Button>
          </div>
        </div>

        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 lg:max-w-sm w-full">
          <div class="rounded-xl border border-white/10 bg-white/5 p-4">
            <div class="flex items-center gap-3">
              <div class="h-9 w-9 rounded-full bg-white text-black flex items-center justify-center text-xs font-semibold">
                1
              </div>
              <div>
                <p class="text-[13px] font-medium text-white">Connect metadata</p>
                <p class="text-[11px] text-text-tertiary">
                  Add an API key or enable TVmaze in Settings.
                </p>
              </div>
            </div>
          </div>

          <div class="rounded-xl border border-white/10 bg-white/5 p-4">
            <div class="flex items-center gap-3">
              <div class="h-9 w-9 rounded-full border border-white/20 text-white flex items-center justify-center text-xs font-semibold">
                2
              </div>
              <div>
                <p class="text-[13px] font-medium text-white">Choose a source</p>
                <p class="text-[11px] text-text-tertiary">
                  Pick OMDb, TMDb, TVmaze, or both for the best match rate.
                </p>
              </div>
            </div>
          </div>

          <div class="rounded-xl border border-white/10 bg-white/5 p-4">
            <div class="flex items-center gap-3">
              <div class="h-9 w-9 rounded-full border border-white/20 text-white flex items-center justify-center text-xs font-semibold">
                3
              </div>
              <div>
                <p class="text-[13px] font-medium text-white">Scan & enrich</p>
                <p class="text-[11px] text-text-tertiary">
                  Scan a folder and apply summaries to selected subtitles.
                </p>
              </div>
            </div>
          </div>

          <div class="rounded-xl border border-white/10 bg-white/5 p-4">
            <div class="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-3">
              Progress
            </div>
            <div class="space-y-2 text-[12px] text-text-secondary">
              <div class="flex items-center justify-between">
                <span>API key connected</span>
                {#if apiConfigured}
                  <span class="text-green-400">Done</span>
                {:else}
                  <span class="text-text-tertiary">Pending</span>
                {/if}
              </div>
              <div class="flex items-center justify-between">
                <span>Metadata source selected</span>
                {#if metadataSelected}
                  <span class="text-green-400">Done</span>
                {:else}
                  <span class="text-text-tertiary">Pending</span>
                {/if}
              </div>
              <div class="flex items-center justify-between">
                <span>First scan completed</span>
                {#if hasScanned}
                  <span class="text-green-400">Done</span>
                {:else}
                  <span class="text-text-tertiary">Pending</span>
                {/if}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  {:else if !scanning}
    <!-- Waiting State -->
    <div class="border border-border rounded-2xl p-12 text-center">
      <div class="flex flex-col items-center gap-4">
        <div class="relative">
          <Scan class="w-16 h-16 text-text-tertiary animate-pulse" />
        </div>
        <div>
          <TypewriterQuote style={quoteStyle} />
          <p class="text-[11px] text-text-tertiary">
            Enter a directory path above to begin
          </p>
        </div>
      </div>
    </div>
  {/if}
  {/if}
</div>

<!-- Confirmation Modal -->
{#if showConfirmation}
  <div
    class="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4"
    role="presentation"
  >
    <div
      class="bg-bg-card border border-border rounded-2xl p-8 max-w-md w-full"
      role="dialog"
      tabindex="-1"
      use:clickOutside={cancelProcess}
    >
      <h3 class="text-base font-medium mb-4">Confirm Processing</h3>
      <p class="text-[13px] text-text-secondary mb-2 leading-relaxed">
        Add plot summaries to {pendingProcessFiles.length}
        {pendingProcessFiles.length !== 1 ? "files" : "file"}
      </p>
      <p class="text-[11px] text-text-tertiary mb-6">
        Using <span class="text-white font-medium"
          >{formatMetadataLabel(metadataProvider)}</span
        > as metadata source
      </p>
      <div
        class="px-4 py-3 bg-yellow-500/5 border border-yellow-500/20 rounded-xl mb-8"
      >
        <p class="text-[11px] text-yellow-200">
          Files will be modified. Backups created automatically.
        </p>
      </div>
      <div class="flex gap-3 justify-end">
        <Button
          on:click={cancelProcess}
          variant="ghost"
          size="sm"
          className="text-text-secondary"
        >
          Cancel
        </Button>
        <Button
          on:click={confirmProcess}
          size="sm"
          className="bg-white text-black hover:bg-white/90"
        >
          Confirm
        </Button>
      </div>
    </div>
  </div>
{/if}

<!-- Results Modal -->
{#if processingResults}
  <div
    class="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4"
    role="presentation"
  >
    <div
      class="bg-bg-card border border-border rounded-2xl p-8 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
      role="dialog"
      tabindex="-1"
      use:clickOutside={closeResults}
    >
      <h3 class="text-base font-medium mb-6">Results</h3>

      <div class="grid grid-cols-2 gap-4 mb-6">
        <div
          class="bg-green-500/5 border border-green-500/20 rounded-xl p-5 text-center"
        >
          <div class="text-2xl font-semibold text-green-300">
            {successCount}
          </div>
          <div
            class="text-[11px] text-text-secondary mt-2 uppercase tracking-wide"
          >
            Successful
          </div>
        </div>
        <div
          class="bg-red-500/5 border border-red-500/20 rounded-xl p-5 text-center"
        >
          <div class="text-2xl font-semibold text-red-300">{failureCount}</div>
          <div
            class="text-[11px] text-text-secondary mt-2 uppercase tracking-wide"
          >
            Failed
          </div>
        </div>
      </div>

      <div
        class="border border-border rounded-xl divide-y divide-border max-h-60 overflow-y-auto mb-6"
      >
        {#each processingResults as result}
          <div
            class="px-5 py-4 {result.success
              ? 'bg-green-500/5'
              : 'bg-red-500/5'}"
          >
            <div class="text-[13px] truncate font-medium">
              {result.file.split(/[/\\]/).pop()}
            </div>
            <div class="text-[11px] text-text-tertiary mt-1">
              {result.success ? result.status : result.error || "Failed"}
            </div>
          </div>
        {/each}
      </div>

      <Button
        on:click={closeResults}
        size="lg"
        className="bg-white text-black hover:bg-white/90"
      >
        Close
      </Button>
    </div>
  </div>
{/if}
