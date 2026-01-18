<script>
  import { createEventDispatcher } from "svelte";
  import StatusBadge from "./StatusBadge.svelte";
  import { Button } from "../lib/components/ui/button";
  import { Skeleton } from "../lib/components/ui/skeleton";
  import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
  } from "../lib/components/ui/table";
  import {
    searchTitle,
    saveSuggestedMatches,
    processBatch,
  } from "../lib/api.js";

  const dispatch = createEventDispatcher();

  export let files = [];
  export let onSelectionChange = () => {};
  export let disabled = false;
  export let metadataProvider = "omdb";
  export let metadataLanguage = "";
  export let activeIntegrations = { omdb: true, tmdb: true, tvmaze: true };
  export let loading = false;

  // Pagination
  let currentPage = 1;
  let itemsPerPage = 50;

  $: totalPages = Math.ceil(files.length / itemsPerPage);
  $: paginatedFiles = files.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage,
  );
  $: pageStart = (currentPage - 1) * itemsPerPage + 1;
  $: pageEnd = Math.min(currentPage * itemsPerPage, files.length);

  function goToPage(page) {
    currentPage = Math.max(1, Math.min(page, totalPages));
  }

  function nextPage() {
    if (currentPage < totalPages) currentPage++;
  }

  function prevPage() {
    if (currentPage > 1) currentPage--;
  }

  // Reset to page 1 when files change
  $: if (files) currentPage = 1;

  let showPreview = false;
  let previewFile = null;
  let showTitleSelector = false;
  let titleSelectorFile = null;
  let searchResults = [];
  let searching = false;
  let searchError = null;
  let showMetadataDropup = false;
  let hoveredPlot = null;
  let tooltipPosition = { x: 0, y: 0 };
  let openSearchDropdown = null;
  let searchingInline = {};
  let inlineSearchResults = {};
  let searchInputValues = {};
  let dropdownPosition = { top: 0, right: 0 };
  let buttonRefs = {};
  let expandedRows = {};
  let bulkMatching = false;
  let matchingProgress = {};
  let suggestedMatches = {};
  let bulkApplying = false;
  let bulkApplyProgress = { current: 0, total: 0, currentFile: "" };
  let bulkApplyResults = [];
  let bulkApplyComplete = null; // { successful, failed, total } - shown for 5 seconds after completion
  let hoveredDisabledIntegration = null;

  $: selectedFiles = files.filter((f) => f.selected);
  $: selectedCount = selectedFiles.length;
  $: allSelected = files.length > 0 && files.every((f) => f.selected);
  $: allSelectedOnPage =
    paginatedFiles.length > 0 && paginatedFiles.every((f) => f.selected);
  // Only count suggested matches for files that don't already have plots
  $: matchedFilesCount = Object.keys(suggestedMatches).filter((filePath) => {
    const file = files.find((f) => f.path === filePath);
    return file && file.status !== "Has Plot" && !file.has_plot;
  }).length;
  // Show bulk apply section if there are matches OR if matching is in progress
  $: hasMatches =
    matchedFilesCount > 0 || Object.keys(matchingProgress).length > 0;

  // Debug logging for reactivity
  $: {
    console.log("=== ResultsList Reactive Update ===");
    console.log("Files count:", files.length);
    console.log(
      "SuggestedMatches count:",
      Object.keys(suggestedMatches).length,
    );
    console.log("SuggestedMatches keys:", Object.keys(suggestedMatches));
    console.log(
      "MatchingProgress count:",
      Object.keys(matchingProgress).length,
    );
    console.log("MatchingProgress keys:", Object.keys(matchingProgress));
    console.log("PaginatedFiles count:", paginatedFiles.length);
  }

  function handlePlotMouseEnter(event, file) {
    if (file.plot || file.summary) {
      hoveredPlot = file;
      updateTooltipPosition(event);
    }
  }

  function handlePlotMouseMove(event) {
    if (hoveredPlot) {
      updateTooltipPosition(event);
    }
  }

  function handlePlotMouseLeave() {
    hoveredPlot = null;
  }

  function updateTooltipPosition(event) {
    tooltipPosition = {
      x: event.clientX + 10,
      y: event.clientY + 10,
    };
  }

  function toggleSearchDropdown(file, event) {
    if (openSearchDropdown === file.path) {
      openSearchDropdown = null;
      return;
    }

    // Calculate position from button
    const button = event.currentTarget;
    const rect = button.getBoundingClientRect();

    // Position dropdown to appear above button, ensuring it's visible
    const dropdownHeight = 380; // Reduced from 450 due to more compact design
    const viewportHeight = window.innerHeight;

    // Try to position above the button first
    let top = rect.top - dropdownHeight - 10; // 10px gap

    // If it would go off the top of the screen, position it below instead
    if (top < 20) {
      top = Math.min(rect.bottom + 10, viewportHeight - dropdownHeight - 20);
    }

    // Ensure it's always within viewport bounds
    top = Math.max(20, Math.min(top, viewportHeight - dropdownHeight - 20));

    dropdownPosition = {
      top: top,
      right: window.innerWidth - rect.right,
    };

    openSearchDropdown = file.path;

    // Initialize with extracted title from filename (preserving year if present)
    if (!searchInputValues[file.path]) {
      const cleanTitle = extractSearchableTitle(file.name, file.title);
      searchInputValues[file.path] = cleanTitle;
      searchInputValues = { ...searchInputValues };
    }

    // Perform initial search
    performSearch(file);
  }

  function handleAddPlotWithSearch(file, event) {
    // Svelte Button dispatches a custom event; the native MouseEvent is in detail.
    const nativeEvent = event?.detail ?? event;
    // Open dropdown for search
    toggleSearchDropdown(file, nativeEvent);
  }

  function handleQuickAddPlot(file) {
    // Close dropdown and process with auto-detection
    openSearchDropdown = null;
    handleProcessSingle(file);
  }

  async function performSearch(file) {
    const query = searchInputValues[file.path]?.trim();
    if (!query) return;

    searchingInline[file.path] = true;
    searchingInline = { ...searchingInline };

    try {
      const response = await searchTitle(query, "quick", {
        preferredSource: metadataProvider,
        language: metadataLanguage,
      });
      inlineSearchResults[file.path] = response.results || [];
      inlineSearchResults = { ...inlineSearchResults };
    } catch (err) {
      console.error("Failed to search for titles:", err);
      inlineSearchResults[file.path] = [];
      inlineSearchResults = { ...inlineSearchResults };
    } finally {
      searchingInline[file.path] = false;
      searchingInline = { ...searchingInline };
    }
  }

  function handleSearchInput(file, event) {
    searchInputValues[file.path] = event.target.value;
    searchInputValues = { ...searchInputValues };
  }

  function handleSearchKeydown(file, event) {
    if (event.key === "Enter") {
      performSearch(file);
    }
  }

  function selectInlineTitle(file, selectedResult) {
    // Store as suggested match instead of immediately processing
    handleManualMatch(file, selectedResult);
    openSearchDropdown = null;
  }

  function toggleSelection(file) {
    file.selected = !file.selected;
    files = [...files];
    onSelectionChange(selectedFiles.map((f) => f.path));
  }

  function toggleAll() {
    const newState = !allSelected;
    files = files.map((f) => ({ ...f, selected: newState }));
    onSelectionChange(selectedFiles.map((f) => f.path));
  }

  function toggleAllOnPage() {
    const newState = !allSelectedOnPage;
    const pagePaths = new Set(paginatedFiles.map((f) => f.path));
    files = files.map((f) =>
      pagePaths.has(f.path) ? { ...f, selected: newState } : f,
    );
    onSelectionChange(selectedFiles.map((f) => f.path));
  }

  async function handleProcessSingle(file) {
    // Show title selector first
    titleSelectorFile = file;
    searching = true;
    searchError = null;
    showTitleSelector = true;

    // Extract clean title from filename (preserving year for better matching)
    const cleanTitle = extractSearchableTitle(file.name, file.title);

    try {
      // Use "full" mode for manual search to get multiple results to choose from
      const response = await searchTitle(cleanTitle, "full", {
        preferredSource: metadataProvider,
        language: metadataLanguage,
      });
      searchResults = response.results || [];
    } catch (err) {
      searchError = "Failed to search for titles. Please try again.";
      searchResults = [];
    } finally {
      searching = false;
    }
  }

  function selectTitle(selectedResult) {
    // Dispatch with selected title info
    // Force reprocess if file already has a plot (this is an update operation)
    dispatch("processSingle", {
      files: [titleSelectorFile.path],
      titleOverride: selectedResult,
      forceReprocess:
        titleSelectorFile.status === "Has Plot" ||
        titleSelectorFile.has_plot === true,
    });
    closeTitleSelector();
  }

  function skipTitleSelection() {
    // Process with automatic title detection
    // Force reprocess if file already has a plot (this is an update operation)
    dispatch("processSingle", {
      files: [titleSelectorFile.path],
      forceReprocess:
        titleSelectorFile.status === "Has Plot" ||
        titleSelectorFile.has_plot === true,
    });
    closeTitleSelector();
  }

  function closeTitleSelector() {
    showTitleSelector = false;
    titleSelectorFile = null;
    searchResults = [];
    searchError = null;
  }

  function handleBulkProcess() {
    const selectedPaths = selectedFiles.map((f) => f.path);
    dispatch("processBulk", { files: selectedPaths });
  }

  async function handleBulkMatch() {
    bulkMatching = true;
    matchingProgress = {};

    for (const file of selectedFiles) {
      matchingProgress[file.path] = "matching";
      matchingProgress = { ...matchingProgress };

      // Extract title and perform search
      const cleanTitle = extractSearchableTitle(file.name, file.title);

      try {
        const response = await searchTitle(cleanTitle, "quick", {
          preferredSource: metadataProvider,
          language: metadataLanguage,
        });
        const results = response.results || [];

        if (results.length > 0) {
          // Store the top result as a suggestion (don't apply yet)
          const topResult = results[0];
          suggestedMatches[file.path] = topResult;
          suggestedMatches = { ...suggestedMatches };
          matchingProgress[file.path] = "matched";
        } else {
          matchingProgress[file.path] = "no-match";
        }
      } catch (err) {
        console.error(`Failed to match ${file.name}:`, err);
        matchingProgress[file.path] = "error";
      }

      matchingProgress = { ...matchingProgress };

      // Small delay to avoid overwhelming the API
      await new Promise((resolve) => setTimeout(resolve, 300));
    }

    bulkMatching = false;

    // Clear progress indicators after 3 seconds
    setTimeout(() => {
      matchingProgress = {};
    }, 3000);
  }

  async function handleBulkApply() {
    // Filter to only files that don't already have plots
    const filesToProcess = Object.keys(suggestedMatches)
      .filter((filePath) => {
        const file = files.find((f) => f.path === filePath);
        return file && file.status !== "Has Plot" && !file.has_plot;
      })
      .map((path) => ({
        path,
        titleOverride: suggestedMatches[path],
      }));

    if (filesToProcess.length === 0) {
      console.log("No files to process");
      return;
    }

    bulkApplying = true;
    bulkApplyProgress = {
      current: 0,
      total: filesToProcess.length,
      currentFile: "",
    };
    bulkApplyResults = [];

    try {
      await processBatch(filesToProcess, null, {
        onStart: (data) => {
          console.log("Bulk apply started:", data.total, "files");
          bulkApplyProgress = { ...bulkApplyProgress, total: data.total };
        },
        onProgress: (data) => {
          bulkApplyProgress = {
            current: data.current,
            total: data.total,
            currentFile: data.file,
          };
        },
        onResult: (data) => {
          bulkApplyResults = [...bulkApplyResults, data];

          // Update the file status in the list
          const fileIndex = files.findIndex(
            (f) => f.path === data.file || f.name === data.file,
          );
          if (fileIndex !== -1 && data.success) {
            files[fileIndex] = {
              ...files[fileIndex],
              status: "Has Plot",
              has_plot: true,
            };
            files = [...files];
          }

          // Remove from suggested matches as it's been processed
          const matchPath = Object.keys(suggestedMatches).find(
            (p) => p === data.file || p.endsWith(data.file),
          );
          if (matchPath) {
            delete suggestedMatches[matchPath];
            suggestedMatches = { ...suggestedMatches };
          }
        },
        onComplete: (data) => {
          console.log(
            "Bulk apply complete:",
            data.successful,
            "/",
            data.total,
            "successful",
          );
          bulkApplying = false;

          // Dispatch event to notify parent of completion
          dispatch("processComplete", {
            successful: data.successful,
            failed: data.failed,
            total: data.total,
          });
        },
        onError: (error) => {
          console.error("Bulk apply error:", error);
          bulkApplying = false;
        },
      });
    } catch (err) {
      console.error("Bulk apply failed:", err);
      bulkApplying = false;
    }
  }

  function removeSuggestedMatch(filePath) {
    delete suggestedMatches[filePath];
    suggestedMatches = { ...suggestedMatches };
  }

  function handleManualMatch(file, selectedResult) {
    // User manually selected a different match
    suggestedMatches[file.path] = selectedResult;
    suggestedMatches = { ...suggestedMatches };
  }

  // Export function for parent component to trigger auto-match
  export async function autoMatchAll() {
    console.log("=== Starting autoMatchAll ===");
    console.log(
      "Current suggestedMatches count:",
      Object.keys(suggestedMatches).length,
    );
    console.log("suggestedMatches paths:", Object.keys(suggestedMatches));
    console.log(
      "Current matchingProgress count:",
      Object.keys(matchingProgress).length,
    );
    console.log("Current files count:", files.length);
    console.log(
      "Files:",
      files.map((f) => ({
        name: f.name,
        path: f.path,
        has_plot: f.has_plot,
        status: f.status,
      })),
    );

    bulkMatching = true;
    // Clear old matching progress for files not in current scan
    const currentFilePaths = files.map((f) => f.path);
    matchingProgress = Object.fromEntries(
      Object.entries(matchingProgress).filter(([path]) =>
        currentFilePaths.includes(path),
      ),
    );
    // Don't reset suggestedMatches - preserve any loaded from database

    for (const file of files) {
      // Show matching status for files with plots (for visual feedback)
      // Don't create suggested matches for them
      if (file.status === "Has Plot" || file.has_plot === true) {
        console.log(`File ${file.name} already has plot, showing as matched`);
        matchingProgress = {
          ...matchingProgress,
          [file.path]: "matched",
        };
        continue;
      }

      // Skip files that already have a suggested match
      if (suggestedMatches[file.path]) {
        console.log(`Skipping ${file.name} - already has suggested match`);
        // Still show the matched status for files with existing matches
        matchingProgress = {
          ...matchingProgress,
          [file.path]: "matched",
        };
        continue;
      }

      matchingProgress = {
        ...matchingProgress,
        [file.path]: "matching",
      };

      const cleanTitle = extractSearchableTitle(file.name, file.title);
      console.log(
        `Auto-matching ${file.name} with search query: "${cleanTitle}"`,
      );

      try {
        const response = await searchTitle(cleanTitle, "quick", {
          preferredSource: metadataProvider,
          language: metadataLanguage,
        });
        const results = response.results || [];

        if (results.length > 0) {
          const topResult = results[0];
          console.log(
            `Match found for ${file.name}: ${topResult.title} (${topResult.year})`,
          );
          // Create new objects to trigger reactivity
          suggestedMatches = {
            ...suggestedMatches,
            [file.path]: topResult,
          };
          matchingProgress = {
            ...matchingProgress,
            [file.path]: "matched",
          };
        } else {
          console.log(
            `No match found for ${file.name} with query "${cleanTitle}"`,
          );
          matchingProgress = {
            ...matchingProgress,
            [file.path]: "no-match",
          };
        }
      } catch (err) {
        console.error(`Failed to match ${file.name}:`, err);
        matchingProgress = {
          ...matchingProgress,
          [file.path]: "error",
        };
      }

      await new Promise((resolve) => setTimeout(resolve, 300));
    }

    bulkMatching = false;

    console.log("=== autoMatchAll complete ===");
    console.log("Final matchingProgress:", matchingProgress);
    console.log(
      "Final suggestedMatches count:",
      Object.keys(suggestedMatches).length,
    );
    console.log("Final suggestedMatches:", suggestedMatches);
    console.log(
      "Sample file paths from files array:",
      files.slice(0, 3).map((f) => f.path),
    );

    // Save all suggested matches to database
    try {
      await saveSuggestedMatches(suggestedMatches);
      console.log("Saved suggested matches to database");
    } catch (err) {
      console.error("Failed to save suggested matches:", err);
    }

    // Keep the matching progress visible (don't clear it after 3 seconds)
    // User can manually clear by rescanning or clicking Clear Results
  }

  // Export function to auto-match a specific batch of files (for streaming)
  export async function autoMatchBatch(batch) {
    console.log("=== Starting autoMatchBatch ===");
    console.log("Batch size:", batch.length);

    for (const file of batch) {
      // Skip files that already have plots
      if (file.status === "Has Plot" || file.has_plot === true) {
        console.log(`File ${file.name} already has plot, showing as matched`);
        matchingProgress = {
          ...matchingProgress,
          [file.path]: "matched",
        };
        continue;
      }

      // Skip files that already have a suggested match
      if (suggestedMatches[file.path]) {
        console.log(`Skipping ${file.name} - already has suggested match`);
        matchingProgress = {
          ...matchingProgress,
          [file.path]: "matched",
        };
        continue;
      }

      matchingProgress = {
        ...matchingProgress,
        [file.path]: "matching",
      };

      const cleanTitle = extractSearchableTitle(file.name, file.title);
      console.log(
        `Auto-matching ${file.name} with search query: "${cleanTitle}"`,
      );

      try {
        const response = await searchTitle(cleanTitle, "quick", {
          preferredSource: metadataProvider,
          language: metadataLanguage,
        });
        const results = response.results || [];

        if (results.length > 0) {
          const topResult = results[0];
          console.log(
            `Match found for ${file.name}: ${topResult.title} (${topResult.year})`,
          );

          suggestedMatches = {
            ...suggestedMatches,
            [file.path]: topResult,
          };
          matchingProgress = {
            ...matchingProgress,
            [file.path]: "matched",
          };

          // Save this match to database immediately
          try {
            await saveSuggestedMatches({ [file.path]: topResult });
          } catch (err) {
            console.error("Failed to save suggested match for", file.name, err);
          }
        } else {
          console.log(
            `No match found for ${file.name} with query "${cleanTitle}"`,
          );
          matchingProgress = {
            ...matchingProgress,
            [file.path]: "no-match",
          };
        }
      } catch (err) {
        console.error(`Failed to match ${file.name}:`, err);
        matchingProgress = {
          ...matchingProgress,
          [file.path]: "error",
        };
      }

      // Small delay between searches to avoid rate limiting
      await new Promise((resolve) => setTimeout(resolve, 300));
    }

    console.log("=== autoMatchBatch complete ===");
  }

  // Export function to load suggested matches from scan result
  export function loadSuggestedMatches(matches) {
    console.log(
      "loadSuggestedMatches called with",
      Object.keys(matches || {}).length,
      "matches",
    );
    suggestedMatches = { ...(matches || {}) };
    // Also populate matching progress for visual indicators
    const newProgress = {};
    for (const filePath in suggestedMatches) {
      newProgress[filePath] = "matched";
    }
    matchingProgress = { ...matchingProgress, ...newProgress };
    console.log(
      "Updated suggestedMatches:",
      Object.keys(suggestedMatches).length,
    );
    console.log(
      "Updated matchingProgress:",
      Object.keys(matchingProgress).length,
    );
  }

  // Export function to load matching progress from scan result
  export function loadMatchingProgress(progress) {
    matchingProgress = progress || {};
  }

  // Export function to clear all matching state
  export function clearMatchingState() {
    console.log("=== Clearing all ResultsList state ===");
    // Reset ALL state variables to guarantee clean slate
    matchingProgress = {};
    suggestedMatches = {};
    searchingInline = {};
    inlineSearchResults = {};
    searchInputValues = {};
    expandedRows = {};
    openSearchDropdown = null;
    bulkMatching = false;
    showTitleSelector = false;
    titleSelectorFile = null;
    searchResults = [];
    searching = false;
    searchError = null;
    showMetadataDropup = false;
    hoveredPlot = null;
    showPreview = false;
    previewFile = null;
    console.log("ResultsList state cleared successfully");
  }

  function openPreview(file) {
    previewFile = file;
    showPreview = true;
  }

  function closePreview() {
    showPreview = false;
    previewFile = null;
  }

  function getMediaType(file) {
    return file.media_type || "N/A";
  }

  function getTitle(file) {
    return file.title || file.name.replace(/\.[^/.]+$/, "");
  }

  function getRating(file) {
    return file.imdb_rating || file.rating || "N/A";
  }

  function getRuntime(file) {
    return file.runtime || "N/A";
  }

  function getPlotPreview(file) {
    if (!file.plot && !file.summary) return "Not loaded";
    const text = file.plot || file.summary;
    return text.length > 100 ? text.substring(0, 100) + "..." : text;
  }

  function hasMetadata(file) {
    // Check if file has meaningful metadata to preview
    return !!(
      file.plot ||
      file.summary ||
      file.title ||
      file.imdb_rating ||
      file.rating ||
      file.runtime
    );
  }

  function toggleMetadataDropup() {
    if (!hasActiveIntegrations) return;
    showMetadataDropup = !showMetadataDropup;
  }

  function selectMetadataSource(source) {
    metadataProvider = source;
    showMetadataDropup = false;
    // Dispatch event to notify parent component
    dispatch("metadataSourceChange", { source });
  }

  function getMetadataSourceLabel() {
    if (!metadataProvider) return "Select source";
    if (metadataProvider === "both") return "OMDb + TMDb";
    if (metadataProvider === "tvmaze") return "TVmaze";
    return metadataProvider.toUpperCase();
  }

  $: omdbActive = activeIntegrations?.omdb ?? false;
  $: tmdbActive = activeIntegrations?.tmdb ?? false;
  $: tvmazeActive = activeIntegrations?.tvmaze ?? false;
  $: hasActiveIntegrations = omdbActive || tmdbActive || tvmazeActive;
  $: if (!hasActiveIntegrations && showMetadataDropup) {
    showMetadataDropup = false;
  }
  $: metadataDropdownOptions = [
    {
      value: "omdb",
      label: "OMDb",
      description: "Open Movie Database",
      enabled: omdbActive,
    },
    {
      value: "tmdb",
      label: "TMDb",
      description: "The Movie Database",
      enabled: tmdbActive,
    },
    {
      value: "tvmaze",
      label: "TVmaze",
      description: "TV metadata without an API key",
      enabled: tvmazeActive,
    },
    {
      value: "both",
      label: "Both",
      description: "OMDb + TMDb fallback",
      enabled: omdbActive && tmdbActive,
    },
  ];

  function toggleRowExpand(filePath) {
    expandedRows[filePath] = !expandedRows[filePath];
    expandedRows = { ...expandedRows };
  }

  /**
   * Sanitizes movie title by removing empty parentheses while preserving valid years
   * @param {string} title - The title to sanitize
   * @returns {string} - The sanitized title
   *
   * Examples:
   * "Xeno ()" → "Xeno"
   * "Xeno ( )" → "Xeno"
   * "Xeno (2025)" → "Xeno (2025)"
   * "Xeno" → "Xeno"
   */
  function sanitizeTitle(title) {
    if (!title) return title;

    // Remove empty parentheses (with optional whitespace inside) and trim
    return title
      .replace(/\(\s*\)/g, "") // Remove () or ( ) or (  ), etc.
      .trim();
  }

  /**
   * Extracts a clean, searchable title from a filename or existing title
   * Removes year, language codes, and quality tags for better OMDb matching
   * @param {string} filename - The filename to extract from (e.g., "Xeno (2025).srt")
   * @param {string} existingTitle - Optional existing title from metadata
   * @returns {string} - Clean title ready for search (without year)
   *
   * Examples:
   * "Eternity (2025).en.srt" → "Eternity"
   * "The.Matrix.1999.srt" → "The Matrix"
   * "Inception_2010.720p.BluRay.srt" → "Inception"
   * "People We Meet on Vacation (2026).srt" → "People We Meet on Vacation"
   */
  function extractSearchableTitle(filename, existingTitle = null) {
    // If we have an existing title from metadata, prefer it
    if (existingTitle) {
      return sanitizeTitle(existingTitle);
    }

    // Remove language codes and subtitle format extensions (e.g., .en.srt, .en.sdh.srt, .eng.srt)
    let title = filename
      .replace(
        /\.(en|eng|es|fr|de|it|pt|ru|ja|zh|ko|ar)\.(sdh|cc|hi|forced)\.srt$/i,
        ".srt",
      ) // Remove language.format.srt
      .replace(/\.(en|eng|es|fr|de|it|pt|ru|ja|zh|ko|ar)\.srt$/i, ".srt") // Remove language.srt
      .replace(/\.[^/.]+$/, ""); // Remove final extension

    // Extract year if present (including in parentheses like "Movie (2024)")
    const yearInParensMatch = title.match(/\((\d{4})\)/);
    const yearStandaloneMatch = title.match(/\b(19|20)\d{2}\b/);
    const year = yearInParensMatch
      ? yearInParensMatch[1]
      : yearStandaloneMatch
        ? yearStandaloneMatch[0]
        : null;

    // Remove common release group tags and quality indicators
    title = title
      .replace(/\[[^\]]+\]/g, "") // Remove anything in square brackets [RARBG], [YTS], etc.
      .replace(
        /\b(REPACK|PROPER|UNRATED|EXTENDED|DIRECTORS?.CUT|DC|THEATRICAL|IMAX)\b/gi,
        "",
      ) // Remove release types
      .replace(
        /\b(720p|1080p|2160p|4k|UHD|HD|SD|BluRay|BRRip|WEB-?DL|WEBRip|HDRip|DVDRip|BDRip)\b/gi,
        "",
      ) // Remove quality tags
      .replace(/\b(x264|x265|H\.?264|H\.?265|HEVC|AAC|AC3|DTS|DD5\.1)\b/gi, "") // Remove codec tags
      .replace(/\b(MULTI|DUAL|SUBBED|DUBBED)\b/gi, "") // Remove audio tags
      .replace(/\-[A-Z0-9]+$/i, "") // Remove release group at end (-RARBG, -YTS, etc.)
      .replace(/[._\-]+/g, " ") // Replace separators with spaces
      .replace(/\s+/g, " ") // Normalize multiple spaces
      .trim();

    // Remove year from the title - OMDb search works better with just the title
    // The year can cause false negatives (e.g., "Eternity 2025" returns nothing, but "Eternity" finds the movie)
    const titleWithoutYear = title
      .replace(/\(?\d{4}\)?/g, "")
      .replace(/\s+/g, " ")
      .trim();

    // Final cleanup
    return sanitizeTitle(titleWithoutYear).trim();
  }
</script>

{#if files.length === 0}
  <div class="py-16 text-center">
    <p class="text-text-secondary">No subtitle files found.</p>
    <p class="text-text-tertiary text-sm mt-1">
      Start a scan to discover SRT files.
    </p>
  </div>
{:else}
  <div class="space-y-4">
    <!-- Bulk Action Toolbar -->
    {#if selectedCount > 0}
      <div class="bg-accent/10 border border-accent/30 rounded-xl px-6 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <svg
              class="w-5 h-5 text-accent"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span class="text-sm font-medium">
              {selectedCount}
              {selectedCount === 1 ? "file" : "files"} selected
            </span>
          </div>
          <div class="flex items-center gap-3">
            <!-- Metadata Source Selector -->
            <div class="relative">
              <button
                on:click={toggleMetadataDropup}
                class="px-4 py-2.5 bg-bg-card border border-white/[0.08] hover:border-white/20
                       text-[13px] font-medium rounded-xl transition-all flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                disabled={!hasActiveIntegrations}
              >
                <svg
                  class="w-4 h-4 text-text-secondary"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
                  />
                </svg>
                <span>{getMetadataSourceLabel()}</span>
                <svg
                  class="w-3.5 h-3.5 text-text-tertiary transition-transform {showMetadataDropup
                    ? 'rotate-180'
                    : ''}"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              <!-- Dropup Menu -->
              {#if showMetadataDropup}
                <div
                  class="absolute top-full mt-2 right-0 w-56 bg-bg-card border border-white/[0.08] rounded-xl shadow-2xl overflow-visible z-50"
                >
                  <div
                    class="px-3 py-2 border-b border-white/[0.08] bg-bg-secondary"
                  >
                    <p
                      class="text-[11px] text-text-tertiary uppercase tracking-wide"
                    >
                      Metadata Source
                    </p>
                  </div>
                  <div class="py-1">
                    {#each metadataDropdownOptions as option}
                      <button
                        on:click={() => option.enabled && selectMetadataSource(option.value)}
                        class="w-full px-4 py-2.5 text-left transition-colors flex items-center justify-between group {option.enabled
                          ? 'hover:bg-bg-hover'
                          : 'opacity-40 cursor-not-allowed'}"
                        disabled={!option.enabled}
                        on:mouseenter={() =>
                          (hoveredDisabledIntegration = option.enabled ? null : option.value)}
                        on:mouseleave={() => (hoveredDisabledIntegration = null)}
                      >
                        <div class="flex items-center gap-3">
                          <div
                            class="w-2 h-2 rounded-full {metadataProvider ===
                            option.value
                              ? 'bg-accent'
                              : 'bg-white/[0.08]'}"
                          ></div>
                          <div>
                            <div class="text-[13px] font-medium">
                              {option.label}
                            </div>
                            <div class="text-[11px] text-text-tertiary">
                              {option.description}
                            </div>
                          </div>
                        </div>
                        {#if metadataProvider === option.value}
                          <svg
                            class="w-4 h-4 text-accent"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        {/if}
                        {#if hoveredDisabledIntegration === option.value}
                          <div
                            class="pointer-events-none absolute right-0 top-1/2 -translate-y-1/2 translate-x-full ml-2 whitespace-nowrap rounded-lg border border-white/10 bg-bg-card px-3 py-2 text-[11px] text-text-secondary shadow-[0_12px_30px_rgba(0,0,0,0.35)] z-50"
                          >
                            Enable this in Settings under Integrations.
                          </div>
                        {/if}
                      </button>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>

            <Button
              on:click={handleBulkMatch}
              disabled={disabled || bulkMatching}
              size="sm"
              className="bg-blue-500 text-white hover:bg-blue-600 gap-2"
            >
              {#if bulkMatching}
                <svg
                  class="w-4 h-4 animate-spin"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Matching...
              {:else}
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                  />
                </svg>
                Bulk Match
              {/if}
            </Button>

            <Button
              on:click={handleBulkProcess}
              {disabled}
              size="sm"
              className="bg-white text-black hover:bg-white/90"
            >
              Add Subtitles to Selected
            </Button>
          </div>
        </div>
      </div>
    {/if}

    <!-- Table -->
    <div class="rounded-lg border border-border bg-card overflow-hidden">
      <div class="max-h-[650px] overflow-y-auto overflow-x-auto">
        <Table className="w-full table-fixed">
          <TableHeader className="sticky top-0 bg-muted/60 backdrop-blur border-b border-border">
            <TableRow className="uppercase tracking-wider">
              <TableHead className="w-12">
                <input
                  type="checkbox"
                  checked={allSelectedOnPage}
                  on:change={toggleAllOnPage}
                  class="h-4 w-4 rounded border-input bg-background text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </TableHead>
              <TableHead className="w-10"></TableHead>
              <TableHead className="w-28">Status</TableHead>
              <TableHead className="w-[38%]">Filename</TableHead>
              <TableHead className="w-[28%]">Matched Result</TableHead>
              <TableHead className="w-64 text-right"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {#if loading && files.length === 0}
              {#each Array(6) as _}
                <TableRow>
                  <TableCell className="w-12">
                    <Skeleton className="h-4 w-4 rounded" />
                  </TableCell>
                  <TableCell className="w-10">
                    <Skeleton className="h-4 w-4" />
                  </TableCell>
                  <TableCell className="w-28">
                    <Skeleton className="h-5 w-20" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-64" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-48" />
                  </TableCell>
                  <TableCell className="w-64">
                    <div class="flex items-center justify-end gap-2">
                      <Skeleton className="h-8 w-24" />
                      <Skeleton className="h-8 w-20" />
                    </div>
                  </TableCell>
                </TableRow>
              {/each}
            {:else}
              {#each paginatedFiles as file (file.path)}
                <TableRow data-state={file.selected ? "selected" : undefined}>
                  <TableCell className="w-12">
                    <input
                      type="checkbox"
                      checked={file.selected}
                      on:change={() => toggleSelection(file)}
                      class="h-4 w-4 rounded border-input bg-background text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    />
                  </TableCell>
                  <TableCell className="w-10">
                    <button
                      on:click={() => toggleRowExpand(file.path)}
                      class="text-text-tertiary hover:text-foreground transition-colors"
                      title="Toggle details"
                    >
                      <svg
                        class="w-4 h-4 transition-transform {expandedRows[
                          file.path
                        ]
                          ? 'rotate-180'
                          : ''}"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </button>
                  </TableCell>
                  <TableCell className="w-28">
                    <StatusBadge status={file.status} />
                  </TableCell>
                  <TableCell className="min-w-0">
                    <span
                      class="text-[13px] font-mono truncate block"
                      title={file.name}
                    >
                      {file.name}
                    </span>
                  </TableCell>
                  <TableCell className="min-w-0">
                    <div class="flex items-center gap-2">
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2">
                          <span class="text-[13px] truncate block">
                            {getTitle(file)}
                          </span>
                          {#if file.title}
                            <span
                              class="px-2 py-0.5 text-[10px] font-medium bg-accent/20 text-accent rounded-full whitespace-nowrap flex-shrink-0"
                            >
                            </span>
                          {/if}
                        </div>

                      <!-- Show suggested match -->
                      {#if suggestedMatches[file.path]}
                        <div class="flex items-center gap-2 mt-1">
                          <span class="text-[11px] text-blue-400"
                            >→ Matched:</span
                          >
                          <span class="text-[11px] text-blue-300 truncate block"
                            >{suggestedMatches[file.path]?.title || "Unknown"} ({suggestedMatches[
                              file.path
                            ]?.year || "N/A"})</span
                          >
                          <button
                            on:click={() => removeSuggestedMatch(file.path)}
                            class="text-blue-400/60 hover:text-blue-300 transition-colors"
                            title="Remove suggestion"
                          >
                            <svg
                              class="w-3 h-3"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M6 18L18 6M6 6l12 12"
                              />
                            </svg>
                          </button>
                        </div>
                      {/if}
                    </div>

                    <!-- Bulk match status indicator -->
                    {#if matchingProgress[file.path]}
                      {#if matchingProgress[file.path] === "matching"}
                        <div
                          class="flex items-center gap-1.5 px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded-full text-[10px] font-medium flex-shrink-0"
                        >
                          <svg
                            class="w-3 h-3 animate-spin"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                            />
                          </svg>
                          Matching
                        </div>
                      {:else if matchingProgress[file.path] === "matched"}
                        <div
                          class="flex items-center gap-1.5 px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full text-[10px] font-medium flex-shrink-0"
                        >
                          <svg
                            class="w-3 h-3"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                          Matched
                        </div>
                      {:else if matchingProgress[file.path] === "no-match"}
                        <div
                          class="flex items-center gap-1.5 px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded-full text-[10px] font-medium flex-shrink-0"
                        >
                          <svg
                            class="w-3 h-3"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                            />
                          </svg>
                          No Match
                        </div>
                      {:else if matchingProgress[file.path] === "error"}
                        <div
                          class="flex items-center gap-1.5 px-2 py-0.5 bg-red-500/20 text-red-400 rounded-full text-[10px] font-medium flex-shrink-0"
                        >
                          <svg
                            class="w-3 h-3"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                          Error
                        </div>
                      {/if}
                    {/if}
                  </div>
                </TableCell>
                <TableCell className="w-64">
                  <div class="flex items-center justify-end gap-2">
                    {#if suggestedMatches[file.path]}
                      <!-- Show quick apply button for suggested matches -->
                      <Button
                        on:click={() => {
                          dispatch("processSingle", {
                            files: [file.path],
                            titleOverride: suggestedMatches[file.path],
                            forceReprocess:
                              file.status === "Has Plot" ||
                              file.has_plot === true,
                          });
                          removeSuggestedMatch(file.path);
                        }}
                        {disabled}
                        size="sm"
                        className="bg-blue-500 text-white hover:bg-blue-600 whitespace-nowrap"
                        title="Apply suggested match"
                      >
                        Apply Match
                      </Button>
                    {/if}
                    <Button
                      on:click={(e) => handleAddPlotWithSearch(file, e)}
                      disabled={disabled || file.status === "Skipped"}
                      size="sm"
                      variant="outline"
                      className="border-green-500 text-green-500 hover:bg-green-500/10 whitespace-nowrap gap-1.5"
                      title={suggestedMatches[file.path]
                        ? "Search for different match"
                        : file.status === "Has Plot"
                          ? "Update plot for this file"
                          : "Add plot to this file"}
                    >
                      <svg
                        class="w-3.5 h-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                        />
                      </svg>
                      {suggestedMatches[file.path]
                        ? "Search"
                        : file.status === "Has Plot"
                          ? "Update"
                          : "Add Plot"}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>

              <!-- Expandable details row -->
              {#if expandedRows[file.path]}
                <TableRow className="bg-muted/40">
                  <TableCell colspan="6">
                    <div class="grid grid-cols-3 gap-6 ml-16">
                      <!-- Rating -->
                      <div>
                        <div
                          class="text-[10px] text-text-tertiary uppercase tracking-wide mb-1.5"
                        >
                          Rating
                        </div>
                        <div class="text-[13px] text-text-secondary">
                          {getRating(file) !== "N/A"
                            ? "⭐ " + getRating(file)
                            : "N/A"}
                        </div>
                      </div>

                      <!-- Runtime -->
                      <div>
                        <div
                          class="text-[10px] text-text-tertiary uppercase tracking-wide mb-1.5"
                        >
                          Runtime
                        </div>
                        <div class="text-[13px] text-text-secondary">
                          {getRuntime(file) !== "N/A"
                            ? "⏱ " + getRuntime(file)
                            : "N/A"}
                        </div>
                      </div>

                      <!-- Year -->
                      <div>
                        <div
                          class="text-[10px] text-text-tertiary uppercase tracking-wide mb-1.5"
                        >
                          Year
                        </div>
                        <div class="text-[13px] text-text-secondary">
                          {file.year || "N/A"}
                        </div>
                      </div>

                      <!-- Plot - Full width -->
                      <div class="col-span-3">
                        <div
                          class="text-[10px] text-text-tertiary uppercase tracking-wide mb-1.5"
                        >
                          Plot Summary
                        </div>
                        <div
                          class="text-[13px] text-text-secondary leading-relaxed bg-bg-primary/50 border border-white/[0.08] rounded-lg p-3"
                        >
                          {#if file.plot || file.summary}
                            {file.plot || file.summary}
                          {:else}
                            <span class="text-text-tertiary italic"
                              >Not loaded</span
                            >
                          {/if}
                        </div>
                      </div>
                    </div>
                  </TableCell>
                </TableRow>
              {/if}
            {/each}
          {/if}
          </TableBody>
        </Table>
      </div>

      <!-- Pagination Controls -->
      {#if totalPages > 1}
        <div
          class="px-6 py-4 bg-bg-secondary border-t border-white/[0.08] flex items-center justify-between"
        >
          <div class="text-[13px] text-text-secondary">
            Showing <span class="text-white font-medium"
              >{pageStart}-{pageEnd}</span
            >
            of <span class="text-white font-medium">{files.length}</span> files
          </div>

          <div class="flex items-center gap-2">
            <button
              on:click={prevPage}
              disabled={currentPage === 1}
              class="px-3 py-1.5 text-[13px] text-text-secondary hover:text-white hover:bg-bg-hover disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-all"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>

            <div class="flex items-center gap-1">
              {#each Array(totalPages) as _, i}
                {@const page = i + 1}
                {#if page === 1 || page === totalPages || (page >= currentPage - 1 && page <= currentPage + 1)}
                  <button
                    on:click={() => goToPage(page)}
                    class="min-w-[32px] px-2 py-1.5 text-[13px] rounded-lg transition-all {page ===
                    currentPage
                      ? 'bg-accent text-white font-medium'
                      : 'text-text-secondary hover:text-white hover:bg-bg-hover'}"
                  >
                    {page}
                  </button>
                {:else if page === currentPage - 2 || page === currentPage + 2}
                  <span class="px-2 text-text-tertiary">...</span>
                {/if}
              {/each}
            </div>

            <button
              on:click={nextPage}
              disabled={currentPage === totalPages}
              class="px-3 py-1.5 text-[13px] text-text-secondary hover:text-white hover:bg-bg-hover disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-all"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          </div>
        </div>
      {/if}
    </div>

    <!-- Bulk Apply Section -->
    {#if hasMatches || bulkApplying}
      <div
        class="bg-blue-500/10 border border-blue-500/30 rounded-xl px-6 py-4"
      >
        {#if bulkApplying}
          <!-- Inline Progress Display -->
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="relative">
                  <svg
                    class="w-5 h-5 text-blue-400 animate-spin"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                </div>
                <div>
                  <span class="text-sm font-medium text-blue-200">
                    Processing {bulkApplyProgress.current} of {bulkApplyProgress.total}
                    files...
                  </span>
                  <p class="text-xs text-blue-300/70 mt-0.5 truncate max-w-md">
                    {bulkApplyProgress.currentFile || "Starting..."}
                  </p>
                </div>
              </div>
              <span class="text-[13px] font-medium text-blue-300 tabular-nums">
                {Math.round(
                  (bulkApplyProgress.current / bulkApplyProgress.total) * 100,
                ) || 0}%
              </span>
            </div>

            <!-- Progress Bar -->
            <div
              class="w-full bg-blue-900/30 rounded-full h-1.5 overflow-hidden"
            >
              <div
                class="bg-blue-400 h-full rounded-full transition-all duration-300 ease-out"
                style="width: {(bulkApplyProgress.current /
                  bulkApplyProgress.total) *
                  100 || 0}%"
              ></div>
            </div>

            <!-- Recent Results -->
            {#if bulkApplyResults.length > 0}
              <div class="flex flex-wrap gap-2 mt-2">
                {#each bulkApplyResults.slice(-5) as result}
                  <span
                    class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] {result.success
                      ? 'bg-green-500/20 text-green-300'
                      : 'bg-red-500/20 text-red-300'}"
                  >
                    {#if result.success}
                      <svg
                        class="w-3 h-3"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    {:else}
                      <svg
                        class="w-3 h-3"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    {/if}
                    {result.file}
                  </span>
                {/each}
              </div>
            {/if}
          </div>
        {:else}
          <!-- Normal Ready State -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <svg
                class="w-5 h-5 text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div>
                {#if matchedFilesCount > 0}
                  <span class="text-sm font-medium text-blue-200">
                    {matchedFilesCount}
                    {matchedFilesCount === 1 ? "file" : "files"} matched and ready
                  </span>
                  <p class="text-xs text-blue-300/70 mt-0.5">
                    Review the suggested matches above, then click "Bulk Apply"
                    to process all
                  </p>
                {:else}
                  <span class="text-sm font-medium text-blue-200">
                    Matching complete
                  </span>
                  <p class="text-xs text-blue-300/70 mt-0.5">
                    All files have been processed or matched
                  </p>
                {/if}
              </div>
            </div>
            {#if matchedFilesCount > 0}
              <Button
                on:click={handleBulkApply}
                {disabled}
                size="sm"
                className="bg-blue-500 text-white hover:bg-blue-600 gap-2"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                Bulk Apply
              </Button>
            {/if}
          </div>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<!-- Search Dropdown (rendered outside table with fixed positioning) -->
{#if openSearchDropdown}
  {@const file = files.find((f) => f.path === openSearchDropdown)}
  {#if file}
    <div
      class="fixed w-96 bg-bg-card border border-white/10 rounded-xl overflow-hidden z-[100]"
      style="top: {dropdownPosition.top}px; right: {dropdownPosition.right}px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3);"
    >
      <!-- Header -->
      <div
        class="px-4 py-3 border-b border-white/[0.08] bg-bg-secondary sticky top-0 z-10"
      >
        <div class="flex items-center justify-between mb-3">
          <p class="text-[11px] text-text-tertiary uppercase tracking-wide">
            {file.status === "Has Plot" ? "Update Plot" : "Add Plot"}
          </p>
          <button
            on:click={() => (openSearchDropdown = null)}
            class="text-text-tertiary hover:text-white transition-colors"
          >
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- Search Input -->
        <div class="relative mb-3">
          <input
            type="text"
            value={searchInputValues[file.path] || ""}
            on:input={(e) => handleSearchInput(file, e)}
            on:keydown={(e) => handleSearchKeydown(file, e)}
            placeholder="Search for title..."
            class="w-full px-3 py-2 pr-10 text-[13px] bg-bg-primary border border-white/20 focus:border-accent rounded-lg transition-all focus:outline-none"
          />
          {#if searchingInline[file.path]}
            <div class="absolute right-3 top-1/2 -translate-y-1/2">
              <div
                class="w-4 h-4 border-2 border-accent/30 border-t-accent rounded-full animate-spin"
              ></div>
            </div>
          {:else}
            <button
              on:click={() => performSearch(file)}
              disabled={!searchInputValues[file.path]?.trim()}
              class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-text-secondary hover:text-accent transition-colors disabled:opacity-30"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </button>
          {/if}
        </div>

        <!-- Quick Action Button -->
        <button
          on:click={() => handleQuickAddPlot(file)}
          class="w-full px-3 py-2 text-[12px] text-accent hover:text-white border border-accent/30 hover:border-accent hover:bg-accent/10 rounded-lg transition-all"
        >
          Use Auto-Detection (Skip Search)
        </button>
      </div>

      <!-- Results Section -->
      <div class="max-h-64 overflow-y-auto">
        {#if inlineSearchResults[file.path]?.length === 0}
          <div class="px-4 py-8 text-center">
            <p class="text-[13px] text-text-secondary">
              No results found for "{searchInputValues[file.path]}"
            </p>
            <p class="text-[11px] text-text-tertiary mt-2">
              Try a different search term or use auto-detection
            </p>
          </div>
        {:else if inlineSearchResults[file.path]}
          <div class="divide-y divide-white/[0.08]">
            {#each [...inlineSearchResults[file.path]].sort((a, b) => {
              const yearA = parseInt(a.year) || 0;
              const yearB = parseInt(b.year) || 0;
              return yearB - yearA;
            }) as result}
              <button
                on:click={() => selectInlineTitle(file, result)}
                class="w-full text-left px-4 py-2.5 hover:bg-accent/10 transition-colors"
              >
                <div class="flex items-start gap-2.5">
                  {#if result.poster && result.poster !== "N/A"}
                    <img
                      src={result.poster}
                      alt={result.title}
                      class="w-10 h-14 object-cover rounded flex-shrink-0"
                    />
                  {:else}
                    <div
                      class="w-10 h-14 bg-bg-secondary rounded flex items-center justify-center flex-shrink-0"
                    >
                      <svg
                        class="w-5 h-5 text-text-tertiary"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"
                        />
                      </svg>
                    </div>
                  {/if}
                  <div class="flex-1 min-w-0">
                    <div class="flex items-baseline gap-2 mb-0.5">
                      <span class="text-[12px] font-medium truncate"
                        >{result.title}</span
                      >
                      <span class="text-[10px] text-text-tertiary flex-shrink-0"
                        >({result.year})</span
                      >
                    </div>
                    <div
                      class="flex items-center gap-2.5 text-[10px] text-text-secondary mb-1"
                    >
                      <span class="capitalize"
                        >{result.media_type || "movie"}</span
                      >
                      {#if result.imdb_rating && result.imdb_rating !== "N/A"}
                        <span>⭐ {result.imdb_rating}</span>
                      {/if}
                      {#if result.runtime && result.runtime !== "N/A"}
                        <span>⏱ {result.runtime}</span>
                      {/if}
                    </div>
                    <p class="text-[10px] text-text-tertiary line-clamp-1">
                      {result.plot}
                    </p>
                  </div>
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}
{/if}

<!-- Preview Modal -->
{#if showPreview && previewFile}
  <div
    class="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4"
    on:click={closePreview}
    role="button"
    tabindex="-1"
    on:keydown={(e) => e.key === "Escape" && closePreview()}
  >
    <div
      class="bg-bg-card border border-border rounded-2xl p-8 max-w-3xl w-full max-h-[90vh] overflow-y-auto"
      on:click|stopPropagation
      role="dialog"
      tabindex="-1"
      on:keydown
    >
      <div class="flex items-start justify-between mb-6">
        <div class="flex-1">
          <h3 class="text-lg font-medium mb-1">{getTitle(previewFile)}</h3>
          <p class="text-sm text-text-secondary font-mono">
            {previewFile.name}
          </p>
        </div>
        <button
          on:click={closePreview}
          class="text-text-secondary hover:text-white transition-colors"
        >
          <svg
            class="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <div class="space-y-6">
        <!-- Status -->
        <div>
          <div class="text-xs text-text-tertiary mb-2 uppercase tracking-wide">
            Status
          </div>
          <StatusBadge status={previewFile.status} />
        </div>

        <!-- Metadata Grid -->
        <div class="grid grid-cols-2 gap-6">
          <div>
            <div
              class="text-xs text-text-tertiary mb-2 uppercase tracking-wide"
            >
              Media Type
            </div>
            <div class="text-sm capitalize">{getMediaType(previewFile)}</div>
          </div>
          <div>
            <div
              class="text-xs text-text-tertiary mb-2 uppercase tracking-wide"
            >
              Rating
            </div>
            <div class="text-sm">{getRating(previewFile)}</div>
          </div>
          <div>
            <div
              class="text-xs text-text-tertiary mb-2 uppercase tracking-wide"
            >
              Runtime
            </div>
            <div class="text-sm">{getRuntime(previewFile)}</div>
          </div>
          <div>
            <div
              class="text-xs text-text-tertiary mb-2 uppercase tracking-wide"
            >
              Year
            </div>
            <div class="text-sm">{previewFile.year || "N/A"}</div>
          </div>
        </div>

        <!-- Plot -->
        <div>
          <div class="text-xs text-text-tertiary mb-2 uppercase tracking-wide">
            Plot Summary
          </div>
          <div
            class="text-sm text-text-secondary leading-relaxed bg-bg-primary/50 border border-white/[0.08] rounded-xl p-4"
          >
            {#if previewFile.plot || previewFile.summary}
              {previewFile.plot || previewFile.summary}
            {:else}
              <span class="text-text-tertiary italic"
                >No plot summary available. Process this file to fetch metadata.</span
              >
            {/if}
          </div>
        </div>

        <!-- File Path -->
        <div>
          <div class="text-xs text-text-tertiary mb-2 uppercase tracking-wide">
            File Path
          </div>
          <div
            class="text-xs text-text-secondary font-mono bg-bg-primary/50 border border-white/[0.08] rounded-xl p-3 break-all"
          >
            {previewFile.path}
          </div>
        </div>

        <!-- Actions -->
        <div
          class="flex items-center justify-end gap-3 pt-4 border-t border-white/[0.08]"
        >
          <button
            on:click={closePreview}
            class="px-5 py-2.5 text-text-secondary hover:text-white text-[13px] transition-colors"
          >
            Close
          </button>
          <button
            on:click={() => {
              handleProcessSingle(previewFile);
              closePreview();
            }}
            disabled={disabled || previewFile.status === "Has Plot"}
            class="px-5 py-2.5 bg-white hover:bg-white/90 disabled:opacity-30 disabled:cursor-not-allowed
                   text-black text-[13px] font-medium rounded-xl transition-all"
          >
            Add Subtitles
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Title Selector Modal -->
{#if showTitleSelector && titleSelectorFile}
  <div
    class="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4"
    on:click={closeTitleSelector}
    role="button"
    tabindex="-1"
    on:keydown={(e) => e.key === "Escape" && closeTitleSelector()}
  >
    <div
      class="bg-bg-card border border-border rounded-2xl p-8 max-w-4xl w-full max-h-[90vh] overflow-y-auto"
      on:click|stopPropagation
      role="dialog"
      tabindex="-1"
      on:keydown
    >
      <div class="flex items-start justify-between mb-6">
        <div>
          <h3 class="text-lg font-medium mb-1">Select Correct Title</h3>
          <p class="text-sm text-text-secondary">
            Choose the correct match for: {titleSelectorFile.name}
          </p>
        </div>
        <button
          on:click={closeTitleSelector}
          class="text-text-secondary hover:text-white transition-colors"
        >
          <svg
            class="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {#if searching}
        <div class="flex items-center justify-center py-16">
          <div class="flex flex-col items-center gap-4">
            <div
              class="w-8 h-8 border-4 border-accent/30 border-t-accent rounded-full animate-spin"
            ></div>
            <p class="text-sm text-text-secondary">Searching for matches...</p>
          </div>
        </div>
      {:else if searchError}
        <div class="bg-red-500/5 border border-red-500/20 rounded-xl p-6 mb-6">
          <p class="text-sm text-red-300">{searchError}</p>
        </div>
        <div class="flex justify-end gap-3">
          <button
            on:click={closeTitleSelector}
            class="px-5 py-2.5 text-text-secondary hover:text-white text-[13px] transition-colors"
          >
            Cancel
          </button>
          <button
            on:click={skipTitleSelection}
            class="px-5 py-2.5 bg-white hover:bg-white/90 text-black text-[13px] font-medium rounded-xl transition-all"
          >
            Use Auto-Detection
          </button>
        </div>
      {:else if searchResults.length === 0}
        <div
          class="bg-yellow-500/5 border border-yellow-500/20 rounded-xl p-6 mb-6"
        >
          <p class="text-sm text-yellow-200">
            No matches found. Would you like to use automatic title detection
            instead?
          </p>
        </div>
        <div class="flex justify-end gap-3">
          <button
            on:click={closeTitleSelector}
            class="px-5 py-2.5 text-text-secondary hover:text-white text-[13px] transition-colors"
          >
            Cancel
          </button>
          <button
            on:click={skipTitleSelection}
            class="px-5 py-2.5 bg-white hover:bg-white/90 text-black text-[13px] font-medium rounded-xl transition-all"
          >
            Use Auto-Detection
          </button>
        </div>
      {:else}
        <div class="space-y-3 mb-6">
          {#each searchResults as result}
            <button
              on:click={() => selectTitle(result)}
              class="w-full text-left bg-bg-primary/50 hover:bg-accent/10 border border-white/[0.08] hover:border-accent/30 rounded-xl p-4 transition-all"
            >
              <div class="flex items-start gap-4">
                {#if result.poster && result.poster !== "N/A"}
                  <img
                    src={result.poster}
                    alt={result.title}
                    class="w-16 h-24 object-cover rounded"
                  />
                {:else}
                  <div
                    class="w-16 h-24 bg-bg-secondary rounded flex items-center justify-center"
                  >
                    <svg
                      class="w-8 h-8 text-text-tertiary"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"
                      />
                    </svg>
                  </div>
                {/if}
                <div class="flex-1 min-w-0">
                  <div class="flex items-baseline gap-2 mb-1">
                    <h4 class="text-base font-medium">{result.title}</h4>
                    <span class="text-sm text-text-tertiary"
                      >({result.year})</span
                    >
                  </div>
                  <div
                    class="flex items-center gap-4 text-xs text-text-secondary mb-2"
                  >
                    <span class="capitalize"
                      >{result.media_type || "movie"}</span
                    >
                    {#if result.runtime && result.runtime !== "N/A"}
                      <span>⏱ {result.runtime}</span>
                    {/if}
                    {#if result.imdb_rating && result.imdb_rating !== "N/A"}
                      <span>⭐ {result.imdb_rating}</span>
                    {/if}
                  </div>
                  <p class="text-xs text-text-tertiary line-clamp-2">
                    {result.plot}
                  </p>
                </div>
              </div>
            </button>
          {/each}
        </div>

        <div
          class="flex justify-between items-center pt-4 border-t border-white/[0.08]"
        >
          <button
            on:click={skipTitleSelection}
            class="text-sm text-text-secondary hover:text-white transition-colors"
          >
            None of these? Use auto-detection →
          </button>
          <button
            on:click={closeTitleSelector}
            class="px-5 py-2.5 text-text-secondary hover:text-white text-[13px] transition-colors"
          >
            Cancel
          </button>
        </div>
      {/if}
    </div>
  </div>
{/if}

<!-- Modern Custom Tooltip -->
{#if hoveredPlot}
  <div
    class="fixed z-[100] pointer-events-none"
    style="left: {tooltipPosition.x}px; top: {tooltipPosition.y}px;"
  >
    <div
      class="bg-bg-card border-2 border-accent/30 rounded-xl shadow-2xl p-4 max-w-md animate-in fade-in duration-150"
    >
      <div class="flex items-start gap-3">
        <div class="flex-shrink-0 mt-0.5">
          <svg
            class="w-4 h-4 text-accent"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <div
            class="text-[11px] text-accent font-medium uppercase tracking-wide mb-1.5"
          >
            Full Plot
          </div>
          <div class="text-[13px] text-text-secondary leading-relaxed">
            {hoveredPlot.plot || hoveredPlot.summary}
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}
