from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

from logging_utils import get_logger
from core.subtitle_processor import SubtitleBlock, parse_srt, format_srt

logger = get_logger(__name__)


# ======================================================================
# ENUMERATE ALL .srt FILES IN PROVIDED FOLDERS
# ======================================================================
def enumerate_srt_files(folders: Iterable[str]) -> List[Path]:
    """
    Recursively enumerate all .srt files in the given folders.
    """
    files: List[Path] = []
    logger.info("Starting SRT file enumeration...")

    for folder in folders:
        logger.debug("Inspecting provided folder entry: %r", folder)

        if not folder:
            logger.debug("Skipping empty folder entry.")
            continue

        path = Path(folder)

        if not path.exists():
            logger.warning("Automation folder does not exist: %s", folder)
            continue

        if not path.is_dir():
            logger.warning("Path is not a directory, skipping: %s", folder)
            continue

        logger.info("Scanning folder recursively: %s", folder)
        found = [p for p in path.rglob("*.srt") if p.is_file()]

        logger.info("Found %d SRT files in %s", len(found), folder)

        files.extend(found)

    logger.info("Finished enumeration. Total SRT files: %d", len(files))
    return files


# ======================================================================
# REMOVE SUBTITLE LINES MATCHING PATTERNS
# ======================================================================
def remove_lines_matching_patterns(
    file_path: str,
    patterns: List[str],
    dry_run: bool = False
) -> Tuple[bool, int]:
    """
    Remove any subtitle lines that contain any of the specified patterns.
    """
    logger.info("Starting removal process for file: %s", file_path)

    if not patterns:
        logger.warning("No patterns provided — skipping file.")
        return False, 0

    # Preprocess patterns
    lowered_patterns = [p.lower().strip() for p in patterns if p]
    logger.debug("Normalized matching patterns: %s", lowered_patterns)

    path = Path(file_path)

    if not path.exists():
        logger.error("File not found: %s", file_path)
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read file
    logger.debug("Reading SRT file...")
    content = path.read_text(encoding="utf-8", errors="ignore")

    logger.debug("Parsing SRT blocks...")
    blocks = parse_srt(content)
    logger.info("Parsed %d subtitle blocks from file.", len(blocks))

    removed_lines = 0
    updated_blocks: List[SubtitleBlock] = []

    # ------------------------------------------------------------------
    # Process blocks
    # ------------------------------------------------------------------
    for block in blocks:
        logger.debug("Processing block #%d (%s → %s)",
                     block.index, block.start_time, block.end_time)

        lines = block.text.splitlines()
        kept_lines = []

        for line in lines:
            line_lower = line.lower()

            # Log each check
            match_hit = any(pattern in line_lower for pattern in lowered_patterns)

            if match_hit:
                removed_lines += 1
                logger.debug(
                    "Removing line in block %d: %r (matched pattern)",
                    block.index, line
                )
                continue

            kept_lines.append(line)

        if kept_lines:
            logger.debug(
                "Block %d kept with %d/%d lines remaining.",
                block.index, len(kept_lines), len(lines)
            )
            updated_blocks.append(
                SubtitleBlock(
                    index=block.index,
                    start_time=block.start_time,
                    end_time=block.end_time,
                    text="\n".join(kept_lines).strip(),
                )
            )
        else:
            logger.debug("Block %d removed entirely — all lines matched patterns.", block.index)

    # ------------------------------------------------------------------
    # No changes detected
    # ------------------------------------------------------------------
    if removed_lines == 0:
        logger.info("No lines removed from file: %s", file_path)
        return False, 0

    logger.info(
        "Removed %d lines across SRT blocks (%d remaining blocks → will renumber).",
        removed_lines, len(updated_blocks)
    )

    # ------------------------------------------------------------------
    # Renumber blocks
    # ------------------------------------------------------------------
    renumbered = [
        SubtitleBlock(i + 1, b.start_time, b.end_time, b.text)
        for i, b in enumerate(updated_blocks)
    ]

    logger.debug(
        "Renumbered blocks: old count=%d, new count=%d",
        len(blocks), len(renumbered)
    )

    # ------------------------------------------------------------------
    # Write changes
    # ------------------------------------------------------------------
    if dry_run:
        logger.info("Dry-run mode — changes NOT written to disk for: %s", file_path)
    else:
        logger.info("Writing updated SRT file to disk: %s", file_path)
        path.write_text(format_srt(renumbered), encoding="utf-8")

    logger.info("Completed processing for file: %s", file_path)

    return True, removed_lines
