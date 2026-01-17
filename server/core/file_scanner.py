import logging
import os
import re
from pathlib import Path
from typing import Generator, List, Dict

# ------------------------------------------------------------
# Logging configuration
# ------------------------------------------------------------

logger = logging.getLogger("FileScanner")
logger.setLevel(logging.INFO)  # Change to DEBUG for deep tracing

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# ------------------------------------------------------------
# Import subtitle parser
# ------------------------------------------------------------

import sys
sys.path.insert(0, str(Path(__file__).parent))
from subtitle_processor import parse_srt


class FileScanner:
    """
    Efficient, disk-friendly subtitle scanner.

    - Recursive (os.scandir-based)
    - Streams file reads
    - Batches results
    - Extensive logging for observability
    """

    SUPPORTED_EXTENSIONS = {".srt"}
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
    PLOT_SCAN_LINES = 50
    DEFAULT_BATCH_SIZE = 100

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    @classmethod
    def scan_directory(
        cls,
        directory_path: str | Path,
        batch_size: int = DEFAULT_BATCH_SIZE,
        follow_symlinks: bool = False,
    ) -> Generator[List[Dict], None, None]:
        """
        Recursively scan a directory tree for .srt files.
        Yields batches of metadata dictionaries.
        """
        root = Path(directory_path)

        logger.info("Starting subtitle scan")
        logger.info("Root directory      : %s", root)
        logger.info("Batch size          : %s", batch_size)
        logger.info("Follow symlinks     : %s", follow_symlinks)

        if not root.exists():
            logger.error("Scan failed: path does not exist (%s)", root)
            raise ValueError(f"Directory does not exist: {directory_path}")

        if not root.is_dir():
            logger.error("Scan failed: not a directory (%s)", root)
            raise ValueError(f"Invalid directory: {directory_path}")

        batch: List[Dict] = []
        total_seen = 0
        total_srt = 0
        total_skipped = 0

        for file_path in cls._walk_files(root, follow_symlinks):
            total_seen += 1

            if file_path.suffix.lower() not in cls.SUPPORTED_EXTENSIONS:
                logger.debug("Ignoring non-subtitle file: %s", file_path)
                continue

            total_srt += 1
            logger.debug("Found subtitle file: %s", file_path)

            # --------------------------------------------
            # Stat / size guard
            # --------------------------------------------

            try:
                stat = file_path.stat()
            except OSError as e:
                total_skipped += 1
                logger.warning(
                    "Skipping unreadable file: %s (%s)",
                    file_path, e
                )
                continue

            if stat.st_size > cls.MAX_FILE_SIZE_BYTES:
                total_skipped += 1
                logger.warning(
                    "Skipping large subtitle file (%d bytes): %s",
                    stat.st_size, file_path
                )
                continue

            # --------------------------------------------
            # Plot detection
            # --------------------------------------------

            try:
                has_plot = cls._check_has_plot(file_path)
                logger.debug(
                    "Plot check for %s: %s",
                    file_path.name,
                    "FOUND" if has_plot else "NOT FOUND"
                )
            except Exception as e:
                total_skipped += 1
                logger.error(
                    "Plot scan failed for %s: %s",
                    file_path, e
                )
                continue

            metadata = {}

            if has_plot:
                try:
                    metadata = cls._extract_metadata(file_path)
                    logger.debug(
                        "Extracted metadata from %s: %s",
                        file_path.name,
                        {k: v for k, v in metadata.items() if v}
                    )
                except Exception as e:
                    logger.warning(
                        "Metadata extraction failed for %s: %s",
                        file_path.name, e
                    )

            batch.append({
                "path": str(file_path),
                "name": file_path.name,
                "has_plot": has_plot,
                "status": "Has Plot" if has_plot else "Not Loaded",
                "summary": metadata.get("summary", ""),
                "plot": metadata.get("summary", ""),
                "title": metadata.get("title"),
                "year": metadata.get("year"),
                "imdb_rating": metadata.get("imdb_rating"),
                "rating": metadata.get("imdb_rating"),
                "runtime": metadata.get("runtime"),
                "selected": False,
            })

            if len(batch) >= batch_size:
                logger.info(
                    "Yielding batch (%d items, %d total files scanned)",
                    len(batch),
                    total_seen
                )
                yield batch
                batch = []

        if batch:
            logger.info(
                "Yielding final batch (%d items)",
                len(batch)
            )
            yield batch

        logger.info("Subtitle scan completed")
        logger.info("Files visited        : %d", total_seen)
        logger.info("Subtitle files found : %d", total_srt)
        logger.info("Files skipped        : %d", total_skipped)

    # --------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------

    @staticmethod
    def _walk_files(root: Path, follow_symlinks: bool):
        """
        Fast iterative recursive directory walk using os.scandir.
        """
        logger.debug("Beginning recursive walk at %s", root)
        stack = [root]

        while stack:
            current = stack.pop()
            logger.debug("Scanning directory: %s", current)

            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        try:
                            if entry.is_dir(follow_symlinks=follow_symlinks):
                                stack.append(Path(entry.path))
                            elif entry.is_file():
                                yield Path(entry.path)
                        except OSError as e:
                            logger.debug(
                                "Skipping entry due to OS error: %s (%s)",
                                entry.path, e
                            )
            except OSError as e:
                logger.warning(
                    "Cannot access directory: %s (%s)",
                    current, e
                )

    @classmethod
    def _check_has_plot(cls, file_path: Path) -> bool:
        """
        Check first N lines for Sublogue signature.
        """
        logger.debug("Scanning for plot marker in %s", file_path.name)

        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f):
                    if i >= cls.PLOT_SCAN_LINES:
                        break
                    if "generated by sublogue" in line.lower():
                        logger.debug(
                            "Plot marker found in %s (line %d)",
                            file_path.name, i + 1
                        )
                        return True
        except Exception as e:
            logger.error(
                "Error reading file during plot scan: %s (%s)",
                file_path, e
            )

        return False

    @classmethod
    def _extract_metadata(cls, file_path: Path) -> Dict:
        """
        Extract title, year, rating, runtime, and plot
        from Sublogue-generated subtitles.
        """
        logger.debug("Extracting metadata from %s", file_path.name)

        content = file_path.read_text(encoding="utf-8", errors="ignore")
        blocks = parse_srt(content)

        metadata = {
            "title": None,
            "year": None,
            "imdb_rating": None,
            "runtime": None,
            "summary": ""
        }

        if len(blocks) < 2:
            logger.debug("Not enough subtitle blocks for metadata extraction")
            return metadata

        # --------------------------------------------
        # Plot block (index 1)
        # --------------------------------------------

        plot_text = blocks[1].text
        plot_text = plot_text.split("Generated by Sublogue")[0].strip()
        metadata["summary"] = plot_text

        # --------------------------------------------
        # Header block (index 0)
        # --------------------------------------------

        header_lines = blocks[0].text.split("\n")

        if header_lines:
            first_line = header_lines[0]
            year_match = re.search(r"\((\d{4})\)", first_line)
            if year_match:
                metadata["year"] = year_match.group(1)
                metadata["title"] = first_line[:year_match.start()].strip()
            else:
                metadata["title"] = first_line.strip()

        if len(header_lines) > 1:
            second_line = header_lines[1]

            rating_match = re.search(r"IMDb:\s*([^\s]+)", second_line)
            if rating_match:
                metadata["imdb_rating"] = rating_match.group(1)

            runtime_match = re.search(r"⏱\s*(.+)", second_line)
            if runtime_match:
                metadata["runtime"] = runtime_match.group(1).strip()

        logger.debug("Metadata extracted: %s", metadata)
        return metadata
