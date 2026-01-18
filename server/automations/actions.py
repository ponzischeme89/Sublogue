from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

from logging_utils import get_logger
from core.subtitle_processor import SubtitleBlock, parse_srt, format_srt

logger = get_logger(__name__)


def enumerate_srt_files(folders: Iterable[str]) -> List[Path]:
    files: List[Path] = []
    for folder in folders:
        if not folder:
            continue
        path = Path(folder)
        if not path.exists():
            logger.warning("Automation folder does not exist: %s", folder)
            continue
        if not path.is_dir():
            continue
        files.extend([p for p in path.rglob("*.srt") if p.is_file()])
    return files


def remove_lines_matching_patterns(file_path: str, patterns: List[str], dry_run: bool = False) -> Tuple[bool, int]:
    """Remove subtitle lines containing any of the provided patterns."""
    if not patterns:
        return False, 0

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = path.read_text(encoding="utf-8", errors="ignore")
    blocks = parse_srt(content)

    lowered_patterns = [p.lower() for p in patterns if p]
    removed_lines = 0
    updated_blocks: List[SubtitleBlock] = []

    for block in blocks:
        lines = block.text.splitlines()
        kept_lines = []
        for line in lines:
            line_lower = line.lower()
            if any(pattern in line_lower for pattern in lowered_patterns):
                removed_lines += 1
                continue
            kept_lines.append(line)

        if kept_lines:
            updated_blocks.append(
                SubtitleBlock(
                    index=block.index,
                    start_time=block.start_time,
                    end_time=block.end_time,
                    text="\n".join(kept_lines).strip(),
                )
            )

    if removed_lines == 0:
        return False, 0

    renumbered = [
        SubtitleBlock(i + 1, b.start_time, b.end_time, b.text)
        for i, b in enumerate(updated_blocks)
    ]

    if not dry_run:
        path.write_text(format_srt(renumbered), encoding="utf-8")

    return True, removed_lines
