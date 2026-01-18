from __future__ import annotations

import re
import logging
import textwrap
import time
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional
from contextlib import contextmanager

# Import keyword stripper for filename cleaning
from core.keyword_stripper import get_stripper

# Cross-platform file locking
try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False
    try:
        import msvcrt
        _HAS_MSVCRT = True
    except ImportError:
        _HAS_MSVCRT = False

logger = logging.getLogger("SubtitleProcessor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ============================================================
# Sentinel tag for deterministic detection
# ============================================================
# This tag is used to mark Sublogue-generated blocks.
# It's deliberately unusual to never appear in real dialogue.
SUBLOGUE_SENTINEL = "{SUBLOGUE}"

# Regex pattern to match ALL Sublogue-style tokens for sanitization
# Matches: {SUBLOGUE}, {SUBLOGUE:anything}, {SUBLOGUE:123}, etc.
SUBLOGUE_TOKEN_PATTERN = re.compile(r"\{SUBLOGUE(?::[^}]*)?\}", re.IGNORECASE)

# ============================================================
# Reading time configuration (WPM-based timing model)
# ============================================================
# These constants define the reading speed model for subtitle timing.
# Based on research showing average reading speeds of 150-250 WPM,
# with 160 WPM being comfortable for on-screen subtitle consumption.

READING_WPM = 160          # Words per minute - comfortable reading pace
MIN_DURATION_SECONDS = 1.2  # Minimum time any subtitle should display
MAX_DURATION_SECONDS = 6.0  # Maximum time before text becomes stale

# ============================================================
# File locking for concurrency protection
# ============================================================
# Prevents race conditions where two tasks both pass _has_plot_fast()
# before either writes, causing duplicate plot insertions.

class FileLockError(Exception):
    """Raised when a file lock cannot be acquired."""
    pass

@contextmanager
def file_lock(path: Path, timeout: float = 10.0):
    """
    Cross-platform file lock context manager.

    Uses a separate .lock file to avoid interfering with the actual file.
    This ensures atomic operations on subtitle files.

    Args:
        path: Path to the file to lock
        timeout: Maximum time to wait for lock (seconds)

    Raises:
        FileLockError: If lock cannot be acquired within timeout
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_file = None
    start_time = time.monotonic()

    try:
        # Create lock file and acquire lock
        while True:
            try:
                # Try to create lock file exclusively (O_CREAT | O_EXCL)
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                lock_file = os.fdopen(fd, 'w')
                lock_file.write(f"{os.getpid()}\n{time.time()}")
                lock_file.flush()
                break
            except FileExistsError:
                # Lock file exists - check if stale (older than 60 seconds)
                try:
                    lock_stat = lock_path.stat()
                    if time.time() - lock_stat.st_mtime > 60:
                        # Stale lock - remove it
                        logger.warning(f"Removing stale lock file: {lock_path}")
                        lock_path.unlink(missing_ok=True)
                        continue
                except OSError:
                    pass

                # Check timeout
                if time.monotonic() - start_time > timeout:
                    raise FileLockError(
                        f"Could not acquire lock on {path} within {timeout}s"
                    )

                # Wait and retry
                time.sleep(0.1)

        logger.debug(f"Acquired lock: {lock_path}")
        yield

    finally:
        # Release lock
        if lock_file:
            lock_file.close()
        try:
            lock_path.unlink(missing_ok=True)
            logger.debug(f"Released lock: {lock_path}")
        except OSError as e:
            logger.warning(f"Failed to remove lock file {lock_path}: {e}")

# ============================================================
# Data structures
# ============================================================

@dataclass(slots=True)
class SubtitleBlock:
    index: int
    start_time: int
    end_time: int
    text: str

# ============================================================
# Timecode helpers
# ============================================================

_TIMECODE_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)

def _timecode_to_ms(tc: str) -> int:
    h, m, rest = tc.split(":")
    s, ms = rest.split(",")
    return ((int(h) * 3600 + int(m) * 60 + int(s)) * 1000) + int(ms)

def _ms_to_timecode(ms: int) -> str:
    ms = max(ms, 0)
    s, ms = divmod(ms, 1000)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# ============================================================
# Reading time calculation (WPM-based timing)
# ============================================================

def count_words(text: str) -> int:
    """
    Count words in text for reading time calculation.

    Args:
        text: Text to count words in

    Returns:
        Number of words (whitespace-separated tokens)
    """
    # Strip any markup/tokens before counting
    cleaned = SUBLOGUE_TOKEN_PATTERN.sub("", text)
    # Split on whitespace and filter empty strings
    words = [w for w in cleaned.split() if w]
    return len(words)


def calculate_reading_duration_ms(
    text: str,
    wpm: float = READING_WPM,
    min_seconds: float = MIN_DURATION_SECONDS,
    max_seconds: float = MAX_DURATION_SECONDS
) -> int:
    """
    Calculate how long a subtitle should display based on reading time.

    Uses a words-per-minute (WPM) model to determine comfortable reading duration.
    The formula ensures text is displayed long enough to read but not so long
    it becomes stale or boring.

    Formula: duration = words / (WPM / 60)
    Clamped to [MIN_DURATION_SECONDS, MAX_DURATION_SECONDS]

    Args:
        text: The subtitle text to calculate duration for
        wpm: Words per minute reading speed (default: 160 WPM)
        min_seconds: Minimum duration in seconds (default: 1.2s)
        max_seconds: Maximum duration in seconds (default: 6.0s)

    Returns:
        Duration in milliseconds
    """
    word_count = count_words(text)

    # Calculate raw reading time: words / (words per minute / 60 seconds)
    # This gives us seconds needed to read at the given WPM
    words_per_second = wpm / 60.0
    raw_duration_seconds = word_count / words_per_second if words_per_second > 0 else min_seconds

    # Clamp to min/max bounds to ensure comfortable reading
    # Min prevents flash-frames, Max prevents stale text
    clamped_duration_seconds = max(min(raw_duration_seconds, max_seconds), min_seconds)

    # Convert to milliseconds for SRT format
    duration_ms = int(clamped_duration_seconds * 1000)

    logger.debug(
        f"Reading time: {word_count} words @ {wpm} WPM = "
        f"{raw_duration_seconds:.2f}s → clamped to {clamped_duration_seconds:.2f}s ({duration_ms}ms)"
    )

    return duration_ms


def split_text_into_readable_chunks(
    text: str,
    max_duration_ms: int,
    wpm: float = READING_WPM,
    min_chunk_duration_ms: int = int(MIN_DURATION_SECONDS * 1000),
    max_chunk_duration_ms: int = int(MAX_DURATION_SECONDS * 1000),
) -> List[str]:
    """
    Split long text into multiple chunks, each sized for comfortable reading.

    This ensures long plot descriptions are broken into digestible pieces
    that fit within the available time window and respect reading speed limits.

    Strategy:
    1. Calculate how many words fit in max_chunk_duration at given WPM
    2. Split text at sentence boundaries when possible
    3. Fall back to word boundaries if sentences are too long

    Args:
        text: Full text to split
        max_duration_ms: Maximum time available for all chunks
        wpm: Words per minute reading speed
        min_chunk_duration_ms: Minimum display time per chunk
        max_chunk_duration_ms: Maximum display time per chunk

    Returns:
        List of text chunks, each sized for comfortable reading
    """
    if not text.strip():
        return []

    # Calculate max words per chunk based on max duration
    words_per_second = wpm / 60.0
    max_seconds_per_chunk = max_chunk_duration_ms / 1000.0
    max_words_per_chunk = int(words_per_second * max_seconds_per_chunk)

    # Calculate how many chunks we can fit in available time
    min_seconds_per_chunk = min_chunk_duration_ms / 1000.0
    max_chunks = max(1, int(max_duration_ms / min_chunk_duration_ms))

    # If text fits in one chunk, return it
    word_count = count_words(text)
    if word_count <= max_words_per_chunk:
        return [text.strip()]

    # Split into sentences for natural breaks
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    chunks = []
    current_chunk_words = []
    current_word_count = 0

    for sentence in sentences:
        sentence_words = sentence.split()
        sentence_word_count = len(sentence_words)

        # Would adding this sentence exceed chunk word limit?
        if current_word_count + sentence_word_count > max_words_per_chunk and current_chunk_words:
            # Save current chunk
            chunks.append(" ".join(current_chunk_words))
            current_chunk_words = []
            current_word_count = 0

            # Check if we've hit max chunks
            if len(chunks) >= max_chunks - 1:
                # Add remaining text to final chunk (may be truncated in display)
                remaining_sentences = sentences[sentences.index(sentence):]
                remaining_text = " ".join(remaining_sentences)
                chunks.append(remaining_text)
                break

        # Add sentence to current chunk
        current_chunk_words.extend(sentence_words)
        current_word_count += sentence_word_count

    # Don't forget the last chunk
    if current_chunk_words and len(chunks) < max_chunks:
        chunks.append(" ".join(current_chunk_words))

    # Limit to max_chunks
    if len(chunks) > max_chunks:
        chunks = chunks[:max_chunks]

    return chunks if chunks else [text.strip()]

# ============================================================
# Sanitization - remove internal markers from output
# ============================================================

def sanitize_subtitle_text(text: str) -> str:
    """
    Remove all internal Sublogue markers from subtitle text.

    This is a DEFENSIVE sanitization pass that ensures no internal
    placeholders or tokens leak into the final SRT output.

    Removes:
    - {SUBLOGUE}
    - {SUBLOGUE:*} (any variant with parameters)
    - Any future Sublogue-style tokens

    Args:
        text: Raw subtitle text potentially containing markers

    Returns:
        Clean text with all Sublogue markers removed
    """
    # Remove all Sublogue tokens using regex
    cleaned = SUBLOGUE_TOKEN_PATTERN.sub("", text)

    # Clean up any resulting double newlines or leading/trailing whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)  # Collapse multiple newlines
    cleaned = cleaned.strip()

    return cleaned


def sanitize_all_blocks(blocks: List[SubtitleBlock]) -> List[SubtitleBlock]:
    """
    Apply sanitization to all subtitle blocks before final output.

    This is the FINAL DEFENSE against internal markers appearing in output.
    Called just before writing the SRT file to ensure clean output.

    Args:
        blocks: List of subtitle blocks to sanitize

    Returns:
        New list with sanitized text (immutable - creates new blocks)
    """
    sanitized = []
    for block in blocks:
        clean_text = sanitize_subtitle_text(block.text)
        # Only include blocks that have content after sanitization
        if clean_text:
            sanitized.append(SubtitleBlock(
                index=block.index,
                start_time=block.start_time,
                end_time=block.end_time,
                text=clean_text
            ))
    return sanitized

# ============================================================
# Parsing / formatting
# ============================================================

def parse_srt(content: str) -> List[SubtitleBlock]:
    """
    Parse SRT content into subtitle blocks.
    Handles BOM, inconsistent line endings, and malformed blocks.
    Empty subtitle blocks are skipped entirely.

    Args:
        content: Raw SRT file content

    Returns:
        List of parsed subtitle blocks
    """
    # Strip BOM if present
    content = content.lstrip("\ufeff")

    # Normalize line endings (handle \r\n, \n, \r)
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    lines = content.splitlines()
    blocks: List[SubtitleBlock] = []

    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Look for timecode line
        m = _TIMECODE_RE.search(line)
        if not m:
            i += 1
            continue

        try:
            start = _timecode_to_ms(m.group("start"))
            end = _timecode_to_ms(m.group("end"))
        except (ValueError, AttributeError) as e:
            logger.warning(f"Malformed timecode at line {i+1}: {line}")
            i += 1
            continue

        # Try to get index from previous line
        index = 0
        if i > 0 and lines[i - 1].strip().isdigit():
            try:
                index = int(lines[i - 1].strip())
            except ValueError:
                pass

        # Collect subtitle text lines
        i += 1
        text_lines: List[str] = []

        while i < n and lines[i].strip() and not _TIMECODE_RE.search(lines[i]):
            text_lines.append(lines[i])
            i += 1

        text = "\n".join(text_lines).strip()

        # Skip empty subtitle blocks
        if text:
            blocks.append(
                SubtitleBlock(
                    index=index,
                    start_time=start,
                    end_time=end,
                    text=text,
                )
            )

        # Skip trailing empty lines
        while i < n and not lines[i].strip():
            i += 1

    return blocks

def format_srt(subs: List[SubtitleBlock]) -> str:
    out: List[str] = []
    for b in subs:
        out.append(str(b.index))
        out.append(f"{_ms_to_timecode(b.start_time)} --> {_ms_to_timecode(b.end_time)}")
        out.extend(b.text.splitlines())
        out.append("")
    return "\n".join(out).rstrip() + "\n"

# ============================================================
# Subtitle construction helpers
# ============================================================

# TV-safe display constraints
TV_LINE_WIDTH = 55  # Wider lines = fewer line breaks (most TVs handle 55+ chars)
TV_MAX_LINES = 2    # Max 2 lines per subtitle block for readability

def wrap_for_tv(text: str, width: int = TV_LINE_WIDTH, max_lines: int = TV_MAX_LINES) -> str:
    """
    Wrap text for TV display with line limits.

    Args:
        text: Text to wrap
        width: Max characters per line (default 55 for modern TVs)
        max_lines: Max lines to display (default 2)

    Returns:
        Wrapped text, truncated to max_lines with ellipsis if needed
    """
    lines = textwrap.wrap(text, width=width)
    if len(lines) > max_lines:
        # Truncate and add ellipsis
        lines = lines[:max_lines]
        if lines:
            lines[-1] = lines[-1].rstrip() + "..."
    return "\n".join(lines)


def chunk_plot_for_display(
    plot: str,
    available_duration_ms: int,
    min_chunk_duration_ms: int = 3000,
    width: int = TV_LINE_WIDTH,
    max_lines: int = TV_MAX_LINES,
) -> List[str]:
    """
    Split a long plot into multiple chunks for sequential display.

    Each chunk is designed to:
    - Fit within TV_MAX_LINES lines
    - Be readable within its time slot
    - Break at sentence boundaries when possible

    Args:
        plot: Full plot text
        available_duration_ms: Total time available for plot display
        min_chunk_duration_ms: Minimum display time per chunk
        width: Characters per line
        max_lines: Lines per chunk

    Returns:
        List of plot text chunks
    """
    # Calculate max chars per chunk based on lines
    max_chars_per_chunk = width * max_lines

    # How many chunks can we fit?
    max_chunks = max(1, available_duration_ms // min_chunk_duration_ms)

    # If plot fits in one chunk, return it
    if len(plot) <= max_chars_per_chunk:
        return [wrap_for_tv(plot, width, max_lines)]

    # Split into sentences for natural breaks
    sentences = re.split(r'(?<=[.!?])\s+', plot)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # Would adding this sentence exceed chunk size?
        test_chunk = (current_chunk + " " + sentence).strip() if current_chunk else sentence

        if len(test_chunk) <= max_chars_per_chunk:
            current_chunk = test_chunk
        else:
            # Save current chunk if not empty
            if current_chunk:
                chunks.append(wrap_for_tv(current_chunk, width, max_lines))

            # Start new chunk with this sentence
            if len(sentence) <= max_chars_per_chunk:
                current_chunk = sentence
            else:
                # Sentence itself is too long, truncate it
                current_chunk = sentence[:max_chars_per_chunk - 3] + "..."

        # Stop if we've hit max chunks
        if len(chunks) >= max_chunks - 1 and current_chunk:
            break

    # Add final chunk
    if current_chunk:
        chunks.append(wrap_for_tv(current_chunk, width, max_lines))

    # Limit to max_chunks
    if len(chunks) > max_chunks:
        chunks = chunks[:max_chunks]
        # Add ellipsis to last chunk if we truncated
        if chunks:
            last = chunks[-1]
            if not last.endswith("..."):
                chunks[-1] = last.rstrip() + "..."

    return chunks if chunks else [wrap_for_tv(plot[:max_chars_per_chunk - 3] + "...", width, max_lines)]

def _merge_small_trailing_chunks(
    chunks: List[str],
    min_words_for_separate_block: int = 6,
    max_chars_per_chunk: int = TV_LINE_WIDTH * TV_MAX_LINES,
) -> List[str]:
    """
    Merge small trailing chunks with the previous chunk if they fit.

    Avoids creating tiny subtitle blocks for just a few words at the end.
    For example, "from day one." (3 words) should be merged with the previous
    chunk rather than displayed as a separate subtitle.

    Args:
        chunks: List of text chunks
        min_words_for_separate_block: Minimum words to warrant a separate block
        max_chars_per_chunk: Maximum characters allowed per chunk

    Returns:
        List of chunks with small trailing ones merged where possible
    """
    if len(chunks) <= 1:
        return chunks

    result = list(chunks)  # Make a copy

    # Work backwards, merging small chunks into their predecessors
    i = len(result) - 1
    while i > 0:
        current_chunk = result[i]
        current_words = count_words(current_chunk)

        # If this chunk is small enough to consider merging
        if current_words < min_words_for_separate_block:
            prev_chunk = result[i - 1]
            merged = f"{prev_chunk} {current_chunk}"

            # If the merged result fits, do the merge
            if len(merged) <= max_chars_per_chunk:
                result[i - 1] = merged
                result.pop(i)
                logger.debug(
                    f"Merged small chunk ({current_words} words) with previous chunk"
                )

        i -= 1

    return result


def _split_plot_into_display_chunks(
    plot: str,
    width: int = TV_LINE_WIDTH,
    max_lines: int = TV_MAX_LINES,
) -> List[str]:
    """
    Split plot text into display-friendly chunks that preserve ALL text.

    Unlike wrap_for_tv() which truncates, this function ensures every word
    of the plot is included across multiple subtitle blocks if needed.

    Strategy:
    1. Split at sentence boundaries first (natural reading breaks)
    2. Each chunk must fit within TV display constraints (width * max_lines chars)
    3. If a sentence is too long, split at word boundaries
    4. NEVER truncate or add ellipsis - preserve complete plot text

    Args:
        plot: Full plot text to split
        width: Max characters per line
        max_lines: Max lines per subtitle block

    Returns:
        List of text chunks, each fitting TV constraints, preserving ALL text
    """
    if not plot or not plot.strip():
        return []

    max_chars_per_chunk = width * max_lines

    # Split into sentences for natural breaks
    # Match periods, exclamation, question marks followed by space
    sentences = re.split(r'(?<=[.!?])\s+', plot.strip())

    chunks: List[str] = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Test if adding this sentence fits in current chunk
        test_chunk = f"{current_chunk} {sentence}".strip() if current_chunk else sentence

        if len(test_chunk) <= max_chars_per_chunk:
            # Fits - add to current chunk
            current_chunk = test_chunk
        else:
            # Doesn't fit - save current chunk and start new one
            if current_chunk:
                chunks.append(current_chunk)

            # Check if sentence itself fits in one chunk
            if len(sentence) <= max_chars_per_chunk:
                current_chunk = sentence
            else:
                # Sentence is too long - split at word boundaries
                words = sentence.split()
                current_chunk = ""

                for word in words:
                    test_word = f"{current_chunk} {word}".strip() if current_chunk else word

                    if len(test_word) <= max_chars_per_chunk:
                        current_chunk = test_word
                    else:
                        # Save current chunk and start fresh with this word
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = word

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)

    # Verify we preserved all content (sanity check)
    original_words = set(plot.split())
    chunk_words = set(" ".join(chunks).split())
    if original_words != chunk_words:
        logger.warning(
            f"Plot chunking may have lost words! "
            f"Original: {len(original_words)}, Chunks: {len(chunk_words)}"
        )

    logger.debug(f"Split plot into {len(chunks)} chunks: {[len(c) for c in chunks]} chars each")

    return chunks


def strip_existing_plot_blocks(blocks: List[SubtitleBlock]) -> List[SubtitleBlock]:
    """
    Remove any existing Sublogue-generated blocks from the subtitle list.
    This ensures idempotency - running the operation twice won't duplicate plot blocks.

    Returns only the dialogue/original subtitle blocks.

    Detection strategy (DETERMINISTIC):
    ───────────────────────────────────
    Primary: Look for the {SUBLOGUE} sentinel tag - this is definitive.
    Fallback: For legacy files without sentinel, use heuristics:
      1. Look for "Generated by Sublogue" signature
      2. Remove zero-duration blocks (metadata-only)
      3. Remove blocks with metadata markers (IMDb, stars, clock emojis)

    The sentinel tag makes detection 100% reliable and eliminates false positives.
    """
    cleaned_blocks: List[SubtitleBlock] = []

    for block in blocks:
        text = block.text
        text_lower = text.lower()

        # PRIMARY: Deterministic sentinel detection - definitive match
        if SUBLOGUE_SENTINEL in text or SUBLOGUE_TOKEN_PATTERN.search(text):
            logger.debug(f"Stripping Sublogue block (sentinel) at index {block.index}")
            continue

        # FALLBACK: Legacy detection for files without sentinel
        # Skip blocks that contain old Sublogue signature
        if "generated by sublogue" in text_lower:
            logger.debug(f"Stripping Sublogue block (legacy) at index {block.index}")
            continue

        # Skip zero-duration blocks (metadata-only)
        if block.start_time == 0 and block.end_time == 0:
            logger.debug(f"Stripping zero-duration block at index {block.index}")
            continue

        # Skip blocks that contain metadata markers (definitely not dialogue)
        if any(marker in text_lower for marker in ["imdb:", "⭐", "⏱"]):
            logger.debug(f"Stripping metadata block at index {block.index}")
            continue

        # This is a real subtitle - keep it
        cleaned_blocks.append(block)

    logger.info(f"Stripped plot blocks: {len(blocks)} → {len(cleaned_blocks)} blocks")
    return cleaned_blocks


@dataclass
class SubtitleFormatOptions:
    """Configuration options for subtitle formatting."""
    title_bold: bool = True          # Wrap title in <b> tags
    plot_italic: bool = True         # Wrap plot text in <i> tags
    show_director: bool = False      # Include director in header
    show_actors: bool = False        # Include actors in header
    show_released: bool = False      # Include release date in header
    show_genre: bool = False         # Include genre in header


# Default formatting options (used when none provided)
DEFAULT_FORMAT_OPTIONS = SubtitleFormatOptions()


def build_intro_blocks(
    movie: dict,
    plot: str,
    first_subtitle_start_ms: int,
    min_safe_gap_ms: int = 500,  # Minimum gap before first subtitle
    format_options: SubtitleFormatOptions = None,
) -> List[SubtitleBlock]:
    """
    Build intro blocks that appear BEFORE the first real subtitle.
    Uses WPM-based timing for comfortable reading speed.

    ╔══════════════════════════════════════════════════════════════════════════╗
    ║  SAFETY GUARANTEE: This function NEVER modifies existing subtitle timing ║
    ║  All intro blocks are placed in the gap BEFORE the first subtitle        ║
    ║  STRICT INVARIANT: intro_end < first_subtitle_start_ms (ALWAYS)          ║
    ╚══════════════════════════════════════════════════════════════════════════╝

    Header Format:
    ──────────────
    <b>Title</b> (Year)
    ⭐ IMDb: <rating>   🍅 RT: <percent>%   ⏱ <runtime>
    [Optional: Director, Actors, Released, Genre]

    Plot Format:
    ────────────
    Plot: <i>plot text here...</i>

    - Always shows both IMDb and RT ratings
    - If RT is unavailable, explicitly shows "RT: N/A" (never silently omits)
    - Runtime is shown in minutes
    - Formatting (bold/italic) is configurable via format_options

    Timing Strategy (WPM-based):
    ────────────────────────────
    Duration is calculated based on word count and reading speed:
    - Base reading speed: 160 WPM
    - Minimum duration: 1.2 seconds (prevents flash-frames)
    - Maximum duration: 6.0 seconds (prevents stale text)

    Formula: duration = max(min(words / (WPM/60), MAX), MIN)

    The key principle: We find space BEFORE the first subtitle, never shift it.
    If we can't fit content safely, we DON'T INSERT rather than risk overlap.

    Args:
        movie: Movie metadata dict with title, year, imdb_rating, rotten_tomatoes, runtime,
               director, actors, released, genre
        plot: Plot text to inject
        first_subtitle_start_ms: Start time of first real subtitle in milliseconds
        min_safe_gap_ms: Minimum gap to maintain before first subtitle
        format_options: Formatting configuration (bold, italic, extra fields)

    Returns:
        List of intro subtitle blocks with safe timing that won't overlap.
        Returns EMPTY list if insufficient gap exists.
    """
    if format_options is None:
        format_options = DEFAULT_FORMAT_OPTIONS

    title = movie.get("title", "Unknown Title")
    year = movie.get("year", "")

    # ─────────────────────────────────────────────────────────────────────────
    # Extract and validate all metadata fields
    # ─────────────────────────────────────────────────────────────────────────
    imdb_rating = movie.get("imdb_rating") or movie.get("imdbRating") or "N/A"
    if not imdb_rating or imdb_rating in ("", "N/A", None):
        imdb_rating = "N/A"

    rt_rating = movie.get("rotten_tomatoes") or movie.get("rottenTomatoes") or "N/A"
    if not rt_rating or rt_rating in ("", "N/A", None):
        rt_rating = "N/A"

    runtime_raw = movie.get("runtime") or movie.get("Runtime") or "N/A"
    if runtime_raw and runtime_raw != "N/A":
        runtime_match = re.search(r'(\d+)', str(runtime_raw))
        runtime = f"{runtime_match.group(1)} min" if runtime_match else runtime_raw
    else:
        runtime = "N/A"

    # Additional metadata fields
    director = movie.get("director") or movie.get("Director") or "N/A"
    actors = movie.get("actors") or movie.get("Actors") or "N/A"
    released = movie.get("released") or movie.get("Released") or "N/A"
    genre = movie.get("genre") or movie.get("Genre") or "N/A"

    # ─────────────────────────────────────────────────────────────────────────
    # Build header with formatting
    # ─────────────────────────────────────────────────────────────────────────

    # Title line - optionally bold
    title_display = f"<b>{title}</b>" if format_options.title_bold else title
    title_line = f"{title_display} ({year})"

    # Ratings/info line
    info_line = f"⭐ IMDb: {imdb_rating}   🍅 RT: {rt_rating}   ⏱ {runtime}"

    # Build optional extra info lines
    extra_lines = []
    if format_options.show_director and director != "N/A":
        extra_lines.append(f"🎬 Director: {director}")
    if format_options.show_actors and actors != "N/A":
        # Truncate long actor lists to first 3
        actor_list = actors.split(", ")
        if len(actor_list) > 3:
            actors_display = ", ".join(actor_list[:3]) + "..."
        else:
            actors_display = actors
        extra_lines.append(f"🎭 Cast: {actors_display}")
    if format_options.show_released and released != "N/A":
        extra_lines.append(f"📅 Released: {released}")
    if format_options.show_genre and genre != "N/A":
        extra_lines.append(f"🎞 Genre: {genre}")

    # Combine header text
    header_parts = [
        SUBLOGUE_SENTINEL,
        title_line,
        info_line,
    ]
    if extra_lines:
        header_parts.extend(extra_lines)
    header_parts.append("")  # Empty line before attribution
    header_parts.append("— Generated by Sublogue")

    header_text = "\n".join(header_parts)

    # ─────────────────────────────────────────────────────────────────────────
    # Build plot text with "Plot:" prefix and optional italic formatting
    # ─────────────────────────────────────────────────────────────────────────
    wrapped_plot = wrap_for_tv(plot)
    if format_options.plot_italic:
        plot_display = f"<i>{wrapped_plot}</i>"
    else:
        plot_display = wrapped_plot
    plot_text = f"{SUBLOGUE_SENTINEL}\nPlot: {plot_display}"

    # ─────────────────────────────────────────────────────────────────────────
    # Calculate available time window BEFORE first subtitle
    # This is the safe zone where we can insert content without overlap
    # ─────────────────────────────────────────────────────────────────────────
    available_time_ms = first_subtitle_start_ms - min_safe_gap_ms

    logger.info(
        f"Timing analysis: First subtitle at {first_subtitle_start_ms}ms, "
        f"available window: {available_time_ms}ms (with {min_safe_gap_ms}ms safety gap)"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # STRICT NON-OVERLAP: If we can't guarantee intro_end < first_subtitle_start,
    # return empty list rather than risk overlap
    # ─────────────────────────────────────────────────────────────────────────
    min_required_ms = int(MIN_DURATION_SECONDS * 1000) + min_safe_gap_ms
    if first_subtitle_start_ms < min_required_ms:
        logger.warning(
            f"[NO INSERT] Insufficient gap: First subtitle at {first_subtitle_start_ms}ms, "
            f"need at least {min_required_ms}ms. Skipping intro blocks."
        )
        return []

    # Helper to validate end time is strictly before first subtitle
    def safe_end_time(proposed_end: int) -> int:
        """Ensure end time is strictly less than first subtitle start."""
        max_allowed = first_subtitle_start_ms - 1  # At least 1ms gap
        return min(proposed_end, max_allowed)

    # ─────────────────────────────────────────────────────────────────────────
    # FIX #3: Use WPM-based timing instead of arbitrary durations
    # Calculate reading time for header based on word count
    # ─────────────────────────────────────────────────────────────────────────
    header_duration_ms = calculate_reading_duration_ms(header_text)
    plot_duration_ms = calculate_reading_duration_ms(wrapped_plot)

    total_ideal_duration_ms = header_duration_ms + plot_duration_ms

    logger.info(
        f"WPM timing: Header needs {header_duration_ms}ms, Plot needs {plot_duration_ms}ms, "
        f"Total ideal: {total_ideal_duration_ms}ms, Available: {available_time_ms}ms"
    )

    blocks: List[SubtitleBlock] = []

    # ─────────────────────────────────────────────────────────────────────────
    # Split plot into TV-friendly chunks FIRST, then determine timing
    # Each chunk should fit on screen (2 lines max) while preserving ALL text
    # ─────────────────────────────────────────────────────────────────────────
    plot_chunks = _split_plot_into_display_chunks(plot)

    # Helper to format a plot chunk with optional italic and "Plot:" prefix
    def format_plot_chunk(chunk_text: str, is_first_chunk: bool) -> str:
        """Format a plot chunk with appropriate styling."""
        wrapped = wrap_for_tv(chunk_text)
        if format_options.plot_italic:
            styled = f"<i>{wrapped}</i>"
        else:
            styled = wrapped
        # Only add "Plot:" prefix to the first chunk
        if is_first_chunk:
            return f"{SUBLOGUE_SENTINEL}\nPlot: {styled}"
        else:
            return f"{SUBLOGUE_SENTINEL}\n{styled}"

    # Calculate total time needed for all plot chunks
    total_plot_duration_ms = sum(
        calculate_reading_duration_ms(chunk) for chunk in plot_chunks
    )
    total_needed_ms = header_duration_ms + total_plot_duration_ms

    logger.info(
        f"Plot split into {len(plot_chunks)} chunks, "
        f"total plot duration: {total_plot_duration_ms}ms, "
        f"total needed: {total_needed_ms}ms, available: {available_time_ms}ms"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Case 1: Enough time for header + ALL plot chunks at ideal reading speed
    # ─────────────────────────────────────────────────────────────────────────
    if available_time_ms >= total_needed_ms:
        # We have enough time - display everything at comfortable reading pace
        blocks.append(SubtitleBlock(1, 0, header_duration_ms, header_text))

        # Try to merge small trailing chunks with the previous one
        merged_chunks = _merge_small_trailing_chunks(plot_chunks)

        current_ms = header_duration_ms
        for i, chunk in enumerate(merged_chunks):
            chunk_start = current_ms
            # Each chunk gets exactly its reading duration - no padding
            chunk_duration = calculate_reading_duration_ms(chunk)
            chunk_end = safe_end_time(chunk_start + chunk_duration)

            chunk_text = format_plot_chunk(chunk, is_first_chunk=(i == 0))
            blocks.append(SubtitleBlock(len(blocks) + 1, chunk_start, chunk_end, chunk_text))
            current_ms = chunk_end

        logger.info(
            f"[CASE 1] Full intro: Header [0-{header_duration_ms}ms], "
            f"{len(merged_chunks)} plot chunk(s) at ideal pace"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Case 2: Enough time for header + plot chunks, but need to compress timing
    # ─────────────────────────────────────────────────────────────────────────
    elif available_time_ms >= header_duration_ms + int(MIN_DURATION_SECONDS * 1000) * len(plot_chunks):
        # We can fit everything, but need to speed up the pace
        # Try to merge small trailing chunks first
        merged_chunks = _merge_small_trailing_chunks(plot_chunks)

        # Header gets minimum of ideal time or proportional share
        header_end_ms = min(header_duration_ms, max(int(MIN_DURATION_SECONDS * 1000), available_time_ms // (len(merged_chunks) + 1)))
        plot_available_ms = available_time_ms - header_end_ms

        blocks.append(SubtitleBlock(1, 0, header_end_ms, header_text))

        # Distribute time across chunks proportionally to their word count
        total_words = sum(count_words(chunk) for chunk in merged_chunks)
        current_ms = header_end_ms

        for i, chunk in enumerate(merged_chunks):
            chunk_start = current_ms

            # Proportional time based on word count
            chunk_words = count_words(chunk)
            if total_words > 0:
                proportion = chunk_words / total_words
                chunk_duration = max(int(plot_available_ms * proportion), int(MIN_DURATION_SECONDS * 1000))
            else:
                chunk_duration = plot_available_ms // len(merged_chunks)

            chunk_end = safe_end_time(chunk_start + chunk_duration)

            chunk_text = format_plot_chunk(chunk, is_first_chunk=(i == 0))
            blocks.append(SubtitleBlock(len(blocks) + 1, chunk_start, chunk_end, chunk_text))
            current_ms = chunk_end

        logger.info(
            f"[CASE 2] Compressed intro: Header [0-{header_end_ms}ms], "
            f"{len(merged_chunks)} plot chunk(s) compressed"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Case 3: Limited time - show header + as many chunks as fit
    # ─────────────────────────────────────────────────────────────────────────
    elif available_time_ms >= header_duration_ms + int(MIN_DURATION_SECONDS * 1000):
        # Try to merge small trailing chunks first
        merged_chunks = _merge_small_trailing_chunks(plot_chunks)

        header_end_ms = min(header_duration_ms, available_time_ms // 2)

        blocks.append(SubtitleBlock(1, 0, header_end_ms, header_text))

        # Fit as many chunks as we can
        current_ms = header_end_ms
        chunks_added = 0

        for i, chunk in enumerate(merged_chunks):
            remaining_ms = (first_subtitle_start_ms - min_safe_gap_ms) - current_ms
            min_needed = int(MIN_DURATION_SECONDS * 1000)

            if remaining_ms < min_needed:
                break

            chunk_start = current_ms
            chunk_duration = calculate_reading_duration_ms(chunk)
            # Don't exceed remaining time, but respect minimum
            chunk_duration = max(min(chunk_duration, remaining_ms), min_needed)
            chunk_end = safe_end_time(chunk_start + chunk_duration)

            # Check if this is the last chunk we can fit
            is_last_fitting = (i == len(merged_chunks) - 1) or (remaining_ms - chunk_duration < min_needed)

            # If we're truncating and can't fit remaining chunks, combine them
            if is_last_fitting and i < len(merged_chunks) - 1:
                remaining_text = " ".join(merged_chunks[i:])
                chunk = remaining_text  # Will be formatted below

            chunk_text = format_plot_chunk(chunk, is_first_chunk=(chunks_added == 0))
            blocks.append(SubtitleBlock(len(blocks) + 1, chunk_start, chunk_end, chunk_text))
            current_ms = chunk_end
            chunks_added += 1

            if is_last_fitting:
                break

        logger.info(
            f"[CASE 3] Partial intro: Header [0-{header_end_ms}ms], "
            f"{chunks_added}/{len(merged_chunks)} plot chunk(s)"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Case 4: Only enough time for brief header (no plot)
    # ─────────────────────────────────────────────────────────────────────────
    elif available_time_ms >= int(MIN_DURATION_SECONDS * 1000):
        block_end_ms = safe_end_time(first_subtitle_start_ms - min_safe_gap_ms)

        # If we can fit at least a brief title, show it
        brief_text = (
            f"{SUBLOGUE_SENTINEL}\n"
            f"{title} ({year})\n"
            f"— Generated by Sublogue"
        )

        blocks.append(SubtitleBlock(1, 0, block_end_ms, brief_text))

        logger.info(f"[CASE 4] Brief header only: [0-{block_end_ms}ms]")

    # Validate: last block must end before first subtitle
    if blocks:
        assert blocks[-1].end_time < first_subtitle_start_ms, "Intro would overlap first subtitle!"

    return blocks

# ============================================================
# Processor
# ============================================================

class SubtitleProcessor:
    """
    Subtitle processor supporting OMDb, TMDb, and TVmaze.

    Safety Guarantees:
    ──────────────────
    - Header = subtitle 01 (inserted, not shifted)
    - Plot   = subtitle 02 (inserted, not shifted)
    - Original subtitles start at 03+ with ORIGINAL TIMING PRESERVED
    - No subtitle data is lost or truncated
    - Timestamps are NEVER modified on existing blocks
    - Internal markers ({SUBLOGUE}) are NEVER present in final output

    Processing Flow:
    ────────────────
    1. Parse SRT file into blocks
    2. Strip any existing Sublogue metadata (idempotency)
    3. Analyze timing gap before first subtitle
    4. Build intro blocks that fit in available gap (WPM-based timing)
    5. Prepend intro blocks (renumber indices only)
    6. SANITIZE: Remove all internal markers from output
    7. Write atomically via temp file
    """

    MAX_SRT_BYTES = 5 * 1024 * 1024
    PLOT_SCAN_LINES = 40

    def __init__(self, omdb_client=None, tmdb_client=None, tvmaze_client=None, preferred_source="omdb"):
        self.omdb_client = omdb_client
        self.tmdb_client = tmdb_client
        self.tvmaze_client = tvmaze_client
        self.preferred_source = preferred_source

    async def process_file(
        self,
        file_path: str | Path,
        duration: int = 40,
        force_reprocess: bool = False,
        title_override: dict = None,
        format_options: SubtitleFormatOptions = None,
        strip_keywords: bool = True,
        clean_subtitle_content: bool = True,
    ) -> dict:
        """
        Process a subtitle file to add plot information.

        Concurrency Safety:
        ───────────────────
        Uses file locking to prevent race conditions where multiple tasks
        could both pass _has_plot_fast() before either writes, causing
        duplicate plot insertions.

        Args:
            file_path: Path to the SRT file
            duration: Duration in seconds for the plot display (legacy, now uses WPM)
            force_reprocess: If True, reprocess even if plot exists
            title_override: Dict with title metadata to use instead of auto-detection
                          Expected keys: title, year, plot, imdb_rating, rotten_tomatoes, runtime,
                                        media_type, director, actors, released, genre
            format_options: Subtitle formatting configuration (bold, italic, extra fields)
            strip_keywords: If True, remove torrent/release tags from filename before API lookup.
                          This improves matching accuracy by cleaning names like
                          "Movie.2024.1080p.BluRay.x264-GROUP" → "Movie (2024)"
                          IMPORTANT: This ONLY affects the title lookup, NOT the subtitle content or timing.
            clean_subtitle_content: If True, remove embedded ads/watermarks (YTS, RARBG, etc.)
                          from inside subtitle text. This cleans the actual dialogue content.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return self._fail("File not found")

        if file_path.stat().st_size > self.MAX_SRT_BYTES:
            return self._fail("Subtitle file too large")

        # If title_override is provided, use it directly instead of fetching
        # (Do metadata fetch BEFORE acquiring lock to minimize lock hold time)
        if title_override:
            logger.info("Using provided title override for %s: %s", file_path.name, title_override.get("title"))
            movie = dict(title_override)

            # If extra fields are missing, try to enrich from OMDb using IMDb ID.
            missing_fields = ["director", "actors", "released", "genre"]
            has_missing = any(
                not movie.get(field) or movie.get(field) == "N/A"
                for field in missing_fields
            )
            imdb_id = movie.get("imdb_id") or movie.get("imdbID")
            if has_missing and imdb_id and self.omdb_client:
                try:
                    enrichment = await self.omdb_client.fetch_summary_by_imdb_id(imdb_id)
                    if enrichment:
                        for field in missing_fields:
                            if not movie.get(field) or movie.get(field) == "N/A":
                                movie[field] = enrichment.get(field, movie.get(field))
                except Exception as e:
                    logger.warning("Failed to enrich metadata for %s: %s", imdb_id, e)
        else:
            raw_name = file_path.stem
            movie_name, year = self.extract_title_and_year(raw_name, strip_keywords=strip_keywords)
            season, episode = get_stripper().extract_season_episode(raw_name)
            is_series = season is not None or episode is not None

            logger.info("Resolved movie name: '%s' → '%s' (year=%s, strip_keywords=%s)", raw_name, movie_name, year, strip_keywords)

            movie = await self._fetch_summary(
                movie_name,
                year=year,
                is_series=is_series,
                season=season,
                episode=episode,
            )
            if not movie:
                return self._fail("No metadata found")

        plot = movie.get("plot", "").strip()
        if not plot:
            return self._fail("Empty plot")

        # ─────────────────────────────────────────────────────────────────────
        # CRITICAL SECTION: Acquire file lock to prevent concurrent processing
        # This ensures only one task can check + modify the file at a time
        # ─────────────────────────────────────────────────────────────────────
        try:
            with file_lock(file_path, timeout=30.0):
                # Re-check for existing plot INSIDE the lock
                # This is the key to preventing duplicates: check-then-write is atomic
                if self._has_plot_fast(file_path) and not force_reprocess and not title_override:
                    logger.info("Skipping %s (plot already exists - checked under lock)", file_path.name)
                    existing_plot = self._extract_existing_plot(file_path)
                    existing_metadata = self._extract_existing_metadata(file_path)
                    return {
                        "success": True,
                        "status": "Skipped",
                        "summary": existing_plot,
                        **existing_metadata
                    }

                # ─────────────────────────────────────────────────────────────
                # PHASE 1: Parse the original subtitle file
                # ─────────────────────────────────────────────────────────────
                original = file_path.read_text(encoding="utf-8", errors="ignore")
                subs = parse_srt(original)

                if not subs:
                    return self._fail("No valid subtitle blocks found")

                logger.info(f"Parsed {len(subs)} subtitle blocks from {file_path.name}")

                # ─────────────────────────────────────────────────────────────
                # PHASE 2: Strip any existing Sublogue-generated blocks (idempotency)
                # This ensures running the operation multiple times doesn't duplicate
                # ─────────────────────────────────────────────────────────────
                clean_subs = strip_existing_plot_blocks(subs)

                if not clean_subs:
                    return self._fail("No dialogue subtitles found after cleaning")

                # ─────────────────────────────────────────────────────────────
                # PHASE 2.5: Clean embedded ads/watermarks from subtitle content
                # This removes things like "YTS", "RARBG", "OpenSubtitles" etc.
                # from inside the actual subtitle text
                # ─────────────────────────────────────────────────────────────
                if clean_subtitle_content:
                    stripper = get_stripper()
                    original_count = len(clean_subs)

                    # Convert SubtitleBlock to dict format for cleaning
                    blocks_as_dicts = [
                        {"index": b.index, "start_time": b.start_time, "end_time": b.end_time, "text": b.text}
                        for b in clean_subs
                    ]

                    # Clean the content
                    cleaned_dicts = stripper.clean_subtitle_blocks(blocks_as_dicts)

                    # Convert back to SubtitleBlock
                    clean_subs = [
                        SubtitleBlock(d["index"], d["start_time"], d["end_time"], d["text"])
                        for d in cleaned_dicts
                    ]

                    removed_ads = original_count - len(clean_subs)
                    if removed_ads > 0:
                        logger.info(
                            f"Removed {removed_ads} ad/watermark subtitle blocks from {file_path.name}"
                        )

                    if not clean_subs:
                        return self._fail("No dialogue subtitles found after ad removal")

                # ─────────────────────────────────────────────────────────────
                # PHASE 3: Analyze timing - find safe insertion window
                #
                # CRITICAL SAFETY GUARANTEE:
                # ══════════════════════════════════════════════════════════════
                # We NEVER modify the timing of any existing subtitle.
                # The original subtitles are treated as IMMUTABLE.
                #
                # Our intro blocks are inserted into the gap BEFORE first subtitle.
                # If no gap exists, we return empty list (no intro blocks).
                # ══════════════════════════════════════════════════════════════
                # ─────────────────────────────────────────────────────────────
                first_subtitle_start_ms = clean_subs[0].start_time
                last_original_timing = clean_subs[-1].end_time

                logger.info(
                    f"Original subtitle timing: First={_ms_to_timecode(first_subtitle_start_ms)} ({first_subtitle_start_ms}ms), "
                    f"Last={_ms_to_timecode(last_original_timing)} ({last_original_timing}ms)"
                )

                # ─────────────────────────────────────────────────────────────
                # PHASE 4: Build intro blocks that fit in the available gap
                # These will NEVER overlap with or shift existing subtitles
                # Returns EMPTY list if insufficient gap
                # ─────────────────────────────────────────────────────────────
                intro_blocks = build_intro_blocks(
                    movie,
                    plot,
                    first_subtitle_start_ms=first_subtitle_start_ms,
                    min_safe_gap_ms=500,  # 500ms safety buffer before first subtitle
                    format_options=format_options,
                )

                # ─────────────────────────────────────────────────────────────
                # PHASE 5: Combine intro + original subtitles
                #
                # NOTE: We're ONLY renumbering indices (1, 2, 3...), NOT timestamps!
                # The start_time and end_time of clean_subs are PRESERVED EXACTLY.
                # ─────────────────────────────────────────────────────────────
                final = intro_blocks + clean_subs

                # Renumber all blocks sequentially (index only, timing unchanged)
                renumbered = [
                    SubtitleBlock(i + 1, b.start_time, b.end_time, b.text)
                    for i, b in enumerate(final)
                ]

                # Verify timing preservation (sanity check)
                num_intro = len(intro_blocks)
                if len(renumbered) > num_intro:
                    preserved_first = renumbered[num_intro]
                    if preserved_first.start_time != first_subtitle_start_ms:
                        logger.error(
                            f"TIMING CORRUPTION DETECTED! Original first subtitle was at "
                            f"{first_subtitle_start_ms}ms but is now at {preserved_first.start_time}ms"
                        )
                        return self._fail("Internal error: timing corruption detected")

                    logger.info(
                        f"✓ Timing preserved: First original subtitle still at "
                        f"{_ms_to_timecode(preserved_first.start_time)}"
                    )

                # ─────────────────────────────────────────────────────────────
                # PHASE 6: SANITIZE - Remove all internal markers before output
                # FIX #2: This ensures {SUBLOGUE} tokens NEVER appear in final SRT
                # ─────────────────────────────────────────────────────────────
                sanitized = sanitize_all_blocks(renumbered)

                logger.info(
                    f"Sanitized {len(renumbered)} blocks → {len(sanitized)} clean blocks "
                    f"(removed internal markers)"
                )

                # ─────────────────────────────────────────────────────────────
                # PHASE 7: Write output atomically (temp file + rename)
                # ─────────────────────────────────────────────────────────────
                tmp = file_path.with_suffix(".srt.tmp")
                tmp.write_text(format_srt(sanitized), encoding="utf-8")
                tmp.replace(file_path)

                logger.info(
                    f"Successfully wrote {len(sanitized)} blocks to {file_path.name} "
                    f"({num_intro} intro + {len(clean_subs)} original)"
                )

                return {
                    "success": True,
                    "status": "Processed",
                    "summary": plot,
                    "title": movie.get("title"),
                    "year": movie.get("year"),
                    "imdb_rating": movie.get("imdb_rating") or movie.get("imdbRating"),
                    "rotten_tomatoes": movie.get("rotten_tomatoes") or movie.get("rottenTomatoes"),
                    "runtime": movie.get("runtime"),
                    "media_type": movie.get("media_type")
                }

        except FileLockError as e:
            logger.error(f"Could not acquire lock for {file_path.name}: {e}")
            return self._fail(f"File is being processed by another task: {e}")

    # ========================================================
    # Metadata fetching
    # ========================================================

    async def _fetch_summary(
        self,
        movie_name: str,
        year: Optional[str] = None,
        is_series: bool = False,
        season: Optional[int] = None,
        episode: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Fetch metadata from configured sources with fallback.

        Priority:
        1. Preferred source (omdb, tmdb, tvmaze)
        2. Fallback to other source if preferred fails

        Year validation ensures we don't match wrong movies (e.g., "Eternity 2025"
        shouldn't match "From Here to Eternity 1953").
        """
        logger.info("Fetching metadata for '%s' (year=%s)", movie_name, year)

        result = None
        omdb_type = "series" if is_series else "movie"
        tmdb_type = "tv" if is_series else "movie"

        # Try preferred source first
        if self.preferred_source == "tvmaze" and self.tvmaze_client and is_series:
            result = await self.tvmaze_client.fetch_summary(
                movie_name,
                year=year,
                season=season,
                episode=episode,
            )
            if result:
                logger.info("Found metadata via TVmaze: %s (%s)", result.get("title"), result.get("year"))
                return result
        elif self.preferred_source == "tmdb" and self.tmdb_client:
            result = await self.tmdb_client.fetch_summary(
                movie_name,
                media_type=tmdb_type,
                year=year,
                season=season,
                episode=episode,
            )
            if result:
                logger.info("Found metadata via TMDb: %s (%s)", result.get("title"), result.get("year"))
                return result
        elif self.preferred_source == "omdb" and self.omdb_client:
            result = await self.omdb_client.fetch_summary(
                movie_name,
                media_type=omdb_type,
                year=year,
                season=season,
                episode=episode,
            )
            if result:
                logger.info("Found metadata via OMDb: %s (%s)", result.get("title"), result.get("year"))
                return result

        # Fallback to other source
        if not result and self.omdb_client and self.preferred_source != "omdb":
            result = await self.omdb_client.fetch_summary(
                movie_name,
                media_type=omdb_type,
                year=year,
                season=season,
                episode=episode,
            )
            if result:
                logger.info("Found metadata via OMDb (fallback): %s (%s)", result.get("title"), result.get("year"))
                return result

        if not result and self.tmdb_client and self.preferred_source != "tmdb":
            result = await self.tmdb_client.fetch_summary(
                movie_name,
                media_type=tmdb_type,
                year=year,
                season=season,
                episode=episode,
            )
            if result:
                logger.info("Found metadata via TMDb (fallback): %s (%s)", result.get("title"), result.get("year"))
                return result

        if not result and self.tvmaze_client and self.preferred_source != "tvmaze" and is_series:
            result = await self.tvmaze_client.fetch_summary(
                movie_name,
                year=year,
                season=season,
                episode=episode,
            )
            if result:
                logger.info("Found metadata via TVmaze (fallback): %s (%s)", result.get("title"), result.get("year"))
                return result

        logger.warning("No metadata found for '%s' (year=%s) from any source", movie_name, year)
        return None

    # ========================================================
    # Helpers
    # ========================================================

    def _has_plot_fast(self, path: Path) -> bool:
        """
        Fast check for existing Sublogue content using sentinel tag.

        Detection strategy (deterministic):
        ────────────────────────────────────
        Primary: Look for {SUBLOGUE} sentinel - definitive match
        Fallback: Look for legacy "generated by sublogue" signature
        """
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f):
                    if i >= self.PLOT_SCAN_LINES:
                        break
                    # Primary: Sentinel tag (deterministic)
                    if SUBLOGUE_SENTINEL in line:
                        return True
                    # Fallback: Legacy signature
                    if "generated by sublogue" in line.lower():
                        return True
        except OSError:
            pass
        return False

    def _extract_existing_plot(self, path: Path) -> str:
        """Extract the plot summary from a file that already has one"""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            blocks = parse_srt(content)

            # The plot is typically in block 2 (index 1)
            # Block 1 is the header with title/rating/runtime
            if len(blocks) >= 2:
                plot_text = blocks[1].text
                # Remove any "Generated by Sublogue" footer if present
                plot_text = plot_text.split("Generated by Sublogue")[0].strip()
                # Also remove any lingering sentinel tags
                plot_text = SUBLOGUE_TOKEN_PATTERN.sub("", plot_text).strip()
                return plot_text
        except Exception as e:
            logger.warning("Failed to extract existing plot from %s: %s", path.name, e)

        return ""

    def _extract_existing_metadata(self, path: Path) -> dict:
        """Extract metadata (title, rating, runtime, year) from a file that already has a plot"""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            blocks = parse_srt(content)

            # The header is in block 1 (index 0)
            # Format: {title} ({year})
            #         ⭐ IMDb: {rating}   🍅 RT: {percent}%   ⏱ {runtime}
            if len(blocks) >= 1:
                header_text = blocks[0].text
                lines = header_text.split('\n')

                metadata = {
                    "title": None,
                    "year": None,
                    "imdb_rating": None,
                    "rotten_tomatoes": None,
                    "runtime": None
                }

                # Parse first line for title and year
                if len(lines) > 0:
                    first_line = lines[0]
                    # Extract year from parentheses
                    year_match = re.search(r'\((\d{4})\)', first_line)
                    if year_match:
                        metadata["year"] = year_match.group(1)
                        # Title is everything before the year
                        metadata["title"] = first_line[:year_match.start()].strip()
                    else:
                        metadata["title"] = first_line.strip()

                # Parse second line for ratings and runtime
                if len(lines) > 1:
                    second_line = lines[1]
                    # Extract IMDb rating
                    rating_match = re.search(r'IMDb:\s*([^\s]+)', second_line)
                    if rating_match:
                        metadata["imdb_rating"] = rating_match.group(1)

                    # Extract Rotten Tomatoes rating
                    rt_match = re.search(r'RT:\s*([^\s]+)', second_line)
                    if rt_match:
                        metadata["rotten_tomatoes"] = rt_match.group(1)

                    # Extract runtime
                    runtime_match = re.search(r'⏱\s*(.+?)(?:\s{2,}|$)', second_line)
                    if runtime_match:
                        metadata["runtime"] = runtime_match.group(1).strip()

                return metadata

        except Exception as e:
            logger.warning("Failed to extract metadata from %s: %s", path.name, e)

        return {
            "title": None,
            "year": None,
            "imdb_rating": None,
            "rotten_tomatoes": None,
            "runtime": None
        }

    @staticmethod
    def extract_title_and_year(name: str, strip_keywords: bool = True) -> Tuple[str, Optional[str]]:
        """
        Extract movie/show title and year from filename.

        When strip_keywords=True (default), uses the KeywordStripper to remove
        torrent/release tags like quality indicators (1080p, BluRay), codecs (x264, HEVC),
        release groups (YTS, RARBG), and subtitle ads (OpenSubtitles).

        This ONLY affects what title is searched for on OMDb/TMDb/TVmaze.
        It does NOT modify the subtitle file content or timing in any way.

        Examples:
            "Eternity (2025).en" -> ("Eternity", "2025")
            "The.Matrix.1999.BluRay" -> ("The Matrix", "1999")
            "Movie.2024.1080p.BluRay.x264-YTS" -> ("Movie", "2024")
            "Some Movie" -> ("Some Movie", None)

        Args:
            name: Filename (without extension) to parse
            strip_keywords: If True, use KeywordStripper for comprehensive cleaning

        Returns:
            Tuple of (cleaned_title, year_or_none)
        """
        if strip_keywords:
            # Use the comprehensive KeywordStripper
            stripper = get_stripper()
            result = stripper.clean_filename(name, preserve_year=True)

            cleaned_title = result["cleaned_title"]
            year = result["year"]

            # The KeywordStripper appends year in format "Title (year)"
            # We need to separate them for API lookup
            if year and f"({year})" in cleaned_title:
                cleaned_title = cleaned_title.replace(f"({year})", "").strip()

            logger.debug(
                f"KeywordStripper: '{name}' → title='{cleaned_title}', year={year}"
            )

            return cleaned_title, year

        # Fallback: Basic cleaning without KeywordStripper
        # Try to find year in parentheses first: "Movie (2025)"
        paren_match = re.search(r'\((\d{4})\)', name)
        if paren_match:
            year = paren_match.group(1)
            # Remove the (year) from name
            name = name[:paren_match.start()] + name[paren_match.end():]
        else:
            # Try to find standalone year: "Movie.2025.BluRay"
            year_match = re.search(r'\b((?:19|20)\d{2})\b', name)
            year = year_match.group(1) if year_match else None
            # Remove year from name
            if year:
                name = re.sub(r'\b' + year + r'\b', '', name)

        # Clean up the title
        name = re.sub(r"\b(en|eng|english|ita|it|fr|es|de|multi)\b", "", name, flags=re.I)
        name = re.sub(r"[._\-]+", " ", name)
        name = " ".join(name.split()).strip()

        return name, year

    @staticmethod
    def clean_movie_name(name: str) -> str:
        """Legacy method - returns just the title without year."""
        title, _ = SubtitleProcessor.extract_title_and_year(name)
        return title

    @staticmethod
    def _fail(msg: str) -> dict:
        return {"success": False, "error": msg, "status": "Error", "summary": ""}
