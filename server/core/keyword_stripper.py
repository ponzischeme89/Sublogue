"""
Keyword stripper utility - removes common junk keywords from filenames and subtitle content
Optimised for torrent / subtitle garbage while preserving real titles and dialogue
"""

from __future__ import annotations

import re
import logging
from logging_utils import get_logger
from typing import Optional, List

logger = get_logger(__name__)


class KeywordStripper:
    """
    High-performance filename cleaner for movies & TV.

    Design goals:
    - Torrent / subtitle spam annihilation
    - Minimal false positives
    - Regex compiled once
    - Fast enough for large libraries
    """

    # -----------------------------
    # CORE JUNK PATTERNS
    # -----------------------------

    QUALITY = r"""
        \b(
            480p|720p|1080p|2160p|4320p|
            4k|8k|
            hdr|hdr10|hdr10\+|dolby\s*vision|dv|
            bluray|blu[-\s]?ray|bdrip|brrip|bd|
            webrip|web[-\s]?dl|web|
            dvdrip|dvd|dvdscr|
            cam|ts|telesync|telecine|tc|
            hdrip|hdlight
        )\b
    """

    CODECS = r"""
        \b(
            x264|x265|h\.?264|h\.?265|hevc|
            xvid|divx|
            aac|ac3|dts|truehd|atmos|
            dd5\.1|dd\+|
            flac|mp3|opus|
            8bit|10bit|hi10p
        )\b
    """

    TORRENT_GROUPS = r"""
        \b(
            yts(\.mx)?|yify|
            rarbg|eztv|ettv|
            psa|ion10|fgт|fgt|
            tgx|torrentgalaxy|
            1337x|limetorrent|
            ettv|ettv|
            publichd|scene|
            ganool|evo
        )\b
    """

    SUBTITLE_ADS = r"""
        \b(
            opensubtitles|
            subscene|
            addic7ed|
            podnapisi|
            yifysubtitles|
            subtitles?\s*by|
            synced?\s*by|
            encoded?\s*by|
            resynced?\s*by
        )\b
        |
        www\.[a-z0-9\-]+\.(com|org|net)
    """

    LANGUAGES = r"""
        \b(
            eng|english|
            ita|italian|
            fra|french|
            spa|spanish|
            ger|german|
            multi|dubbed|
            vostfr|subfrench|
            subs?|subtitles?
        )\b
    """

    EDITIONS = r"""
        \b(
            unrated|uncut|
            directors?\s*cut|
            extended|
            theatrical|
            imax|
            special\s*edition|
            limited|
            internal|
            proper|repack|real
        )\b
    """

    # -----------------------------
    # STRUCTURAL NOISE
    # -----------------------------

    BRACKETS = r"""
        [\[\(\{]
        .*?
        [\]\)\}]
    """

    SEPARATORS = r"[._\-]+"

    MULTISPACE = r"\s+"

    YEAR_PATTERN = r"(19\d{2}|20\d{2})"

    SEASON_EPISODE = [
        r"[Ss](\d{1,2})[Ee](\d{1,2})",
        r"(\d{1,2})x(\d{1,2})",
        r"Season\s*(\d{1,2})\s*Episode\s*(\d{1,2})",
    ]

    # -----------------------------
    # SUBTITLE CONTENT ADS/WATERMARKS
    # -----------------------------
    # These patterns are specifically for cleaning embedded ads from subtitle TEXT
    # They're more aggressive than filename patterns since we want to remove entire lines

    # Release group watermarks that appear in subtitle text
    SUBTITLE_WATERMARKS = [
        # YTS and variants
        r"yts\.mx",
        r"yts\.am",
        r"yts\.lt",
        r"yts\.ag",
        r"\byts\b",
        r"\byify\b",
        # RARBG and other groups
        r"\brarbg\b",
        r"\beztv\b",
        r"\bettv\b",
        r"torrentgalaxy",
        r"\btgx\b",
        r"1337x",
        r"limetorrents?",
        r"\bevo\b",
        r"\bpsa\b",
        r"\bfgt\b",
        # Subtitle sites
        r"opensubtitles?",
        r"subscene",
        r"addic7ed",
        r"podnapisi",
        r"yifysubtitles?",
        r"sub\.?scene",
        r"legendas\.?tv",
        r"shooter\.?cn",
        r"subhd",
        # Generic patterns
        r"downloaded\s+from",
        r"subtitles?\s+by",
        r"sync(?:ed|hronized)?\s+(?:and\s+)?correct(?:ed|ions?)?\s+by",
        r"ripped\s+by",
        r"encoded?\s+by",
        r"resynce?d?\s+by",
        r"improved\s+by",
        r"fixed\s+by",
        r"translated\s+by",
        r"captioned\s+by",
        r"support\s+us\s+and",
        r"get\s+more\s+subtitles",
        r"quality\s+subtitles",
        r"best\s+subtitles",
        r"free\s+subtitles",
        # URLs and domains
        r"www\.[a-z0-9\-]+\.(com|org|net|io|tv|mx|am|lt|ag)",
        r"https?://[^\s]+",
        # Social media handles that are clearly ads
        r"@yaborr",
        r"@sub_scene",
        r"follow\s+us\s+on",
        r"join\s+us\s+at",
        r"visit\s+us\s+at",
        # Promotional text
        r"advertise\s+here",
        r"membership\s+(is\s+)?free",
        r"become\s+a\s+member",
        r"register\s+(now|today|free)",
        r"sign\s+up\s+(now|today|free)",
    ]

    # Patterns that indicate an ENTIRE subtitle block should be removed
    # (not just the matching text, but the whole block)
    SUBTITLE_BLOCK_REMOVERS = [
        # Pure promotional blocks
        r"^[\s\-_]*(?:www\.)?yts",
        r"^[\s\-_]*(?:www\.)?rarbg",
        r"^[\s\-_]*opensubtitles",
        r"^[\s\-_]*subscene",
        r"^[\s\-_]*downloaded\s+from",
        r"^[\s\-_]*subtitles?\s+by",
        r"^[\s\-_]*sync(?:ed)?\s+(?:and\s+)?correct",
        r"^[\s\-_]*support\s+us",
        r"^[\s\-_]*get\s+(?:more\s+)?subtitles",
        r"^[\s\-_]*quality\s+subtitles",
        r"^[\s\-_]*advertise",
        # ASCII art headers/footers (often used for ads)
        r"^[\s\-=_\*]{10,}$",
        # Empty after cleaning
        r"^\s*$",
    ]

    # -----------------------------
    # COMPILED REGEX CACHE
    # -----------------------------

    _compiled = None

    @classmethod
    def _compile(cls):
        if cls._compiled:
            return cls._compiled

        def c(p):
            return re.compile(p, re.IGNORECASE | re.VERBOSE)

        cls._compiled = {
            "junk": c("|".join([
                cls.QUALITY,
                cls.CODECS,
                cls.TORRENT_GROUPS,
                cls.SUBTITLE_ADS,
                cls.LANGUAGES,
                cls.EDITIONS,
            ])),
            "brackets": c(cls.BRACKETS),
            "separators": re.compile(cls.SEPARATORS),
            "multispace": re.compile(cls.MULTISPACE),
            "year": re.compile(cls.YEAR_PATTERN),
            "season_episode": [re.compile(p, re.IGNORECASE) for p in cls.SEASON_EPISODE],
            # Subtitle content cleaning patterns
            "subtitle_watermarks": [
                re.compile(p, re.IGNORECASE) for p in cls.SUBTITLE_WATERMARKS
            ],
            "subtitle_block_removers": [
                re.compile(p, re.IGNORECASE | re.MULTILINE) for p in cls.SUBTITLE_BLOCK_REMOVERS
            ],
        }

        return cls._compiled

    # -----------------------------
    # PUBLIC API
    # -----------------------------

    def strip_keywords(self, title: str, preserve_year: bool = True) -> str:
        rx = self._compile()

        original = title

        # Extract year early
        year: Optional[str] = None
        if preserve_year:
            m = rx["year"].search(title)
            if m:
                year = m.group(1)

        # Remove obvious junk
        cleaned = rx["junk"].sub("", title)

        # Remove bracketed junk AFTER stripping known keywords
        cleaned = rx["brackets"].sub("", cleaned)

        # Normalize separators
        cleaned = rx["separators"].sub(" ", cleaned)
        cleaned = rx["multispace"].sub(" ", cleaned).strip()

        # Re-append year
        if preserve_year and year and year not in cleaned:
            cleaned = f"{cleaned} ({year})"

        logger.debug("KeywordStripper: '%s' -> '%s'", original, cleaned)
        return cleaned

    def extract_year(self, title: str) -> Optional[str]:
        rx = self._compile()
        m = rx["year"].search(title)
        return m.group(1) if m else None

    def extract_season_episode(self, title: str):
        rx = self._compile()
        for p in rx["season_episode"]:
            m = p.search(title)
            if m:
                return int(m.group(1)), int(m.group(2))
        return None, None

    def clean_filename(self, filename: str, preserve_year: bool = True) -> dict:
        name = re.sub(r"\.[^.]+$", "", filename)

        season, episode = self.extract_season_episode(name)
        year = self.extract_year(name)
        cleaned = self.strip_keywords(name, preserve_year=preserve_year)

        return {
            "cleaned_title": cleaned,
            "year": year,
            "season": season,
            "episode": episode,
            "is_series": season is not None or episode is not None,
        }

    # -----------------------------
    # SUBTITLE CONTENT CLEANING
    # -----------------------------

    def should_remove_subtitle_block(self, text: str) -> bool:
        """
        Check if an entire subtitle block should be removed.

        Returns True if the block is purely promotional/ad content
        with no legitimate dialogue.

        Args:
            text: The subtitle text content

        Returns:
            True if block should be removed entirely
        """
        rx = self._compile()

        # Check each line of the subtitle
        lines = text.strip().split('\n')
        non_ad_lines = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this line matches any block remover pattern
            is_ad_line = False
            for pattern in rx["subtitle_block_removers"]:
                if pattern.search(line):
                    is_ad_line = True
                    break

            # Also check watermarks - if the entire line is just a watermark
            if not is_ad_line:
                temp_line = line
                for pattern in rx["subtitle_watermarks"]:
                    temp_line = pattern.sub("", temp_line)
                # If after removing watermarks, line is empty or just punctuation
                temp_line = re.sub(r'[\s\-_\.\,\!\?\:\;]+', '', temp_line)
                if not temp_line:
                    is_ad_line = True

            if not is_ad_line:
                non_ad_lines += 1

        # If no legitimate content remains, remove the block
        return non_ad_lines == 0

    def clean_subtitle_text(self, text: str) -> str:
        """
        Clean watermarks and ads from subtitle text while preserving dialogue.

        This is more surgical than should_remove_subtitle_block() - it removes
        specific ad text but keeps the rest of the subtitle intact.

        Args:
            text: The subtitle text content

        Returns:
            Cleaned text with ads removed, or empty string if nothing remains
        """
        rx = self._compile()
        original = text

        # Process line by line to handle multi-line subtitles
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            cleaned_line = line

            # Remove watermark patterns
            for pattern in rx["subtitle_watermarks"]:
                cleaned_line = pattern.sub("", cleaned_line)

            # Clean up resulting whitespace
            cleaned_line = re.sub(r'\s+', ' ', cleaned_line).strip()

            # Only keep lines that have content after cleaning
            if cleaned_line:
                cleaned_lines.append(cleaned_line)

        result = '\n'.join(cleaned_lines)

        # Final cleanup - remove lines that are just punctuation/dashes
        result_lines = result.split('\n')
        result_lines = [l for l in result_lines if re.search(r'[a-zA-Z0-9]', l)]
        result = '\n'.join(result_lines)

        if result != original:
            logger.debug("Cleaned subtitle text: '%s' -> '%s'", original[:50], result[:50])

        return result

    def clean_subtitle_blocks(self, blocks: List[dict]) -> List[dict]:
        """
        Clean a list of subtitle blocks, removing ads and watermarks.

        This processes each block:
        1. Checks if the entire block should be removed (pure ad content)
        2. If not, cleans watermarks from the text

        Args:
            blocks: List of subtitle block dicts with 'text' key

        Returns:
            Cleaned list with ad blocks removed and watermarks stripped
        """
        cleaned = []
        removed_count = 0
        modified_count = 0

        for block in blocks:
            text = block.get("text", "")

            # Check if entire block should be removed
            if self.should_remove_subtitle_block(text):
                removed_count += 1
                logger.debug("Removing ad block: '%s'", text[:50])
                continue

            # Clean the text
            cleaned_text = self.clean_subtitle_text(text)

            # Skip if cleaning resulted in empty text
            if not cleaned_text.strip():
                removed_count += 1
                continue

            # Track if we modified the text
            if cleaned_text != text:
                modified_count += 1

            # Create new block with cleaned text
            cleaned_block = block.copy()
            cleaned_block["text"] = cleaned_text
            cleaned.append(cleaned_block)

        if removed_count > 0 or modified_count > 0:
            logger.info(
                "Subtitle cleaning: removed %d ad blocks, modified %d blocks",
                removed_count, modified_count
            )

        return cleaned


# -----------------------------
# SINGLETON HELPERS
# -----------------------------

_default_stripper: Optional[KeywordStripper] = None


def get_stripper() -> KeywordStripper:
    global _default_stripper
    if _default_stripper is None:
        _default_stripper = KeywordStripper()
    return _default_stripper


def clean_title(title: str, preserve_year: bool = True) -> str:
    return get_stripper().strip_keywords(title, preserve_year)


def clean_filename(filename: str, preserve_year: bool = True) -> dict:
    return get_stripper().clean_filename(filename, preserve_year)


def clean_subtitle_content(text: str) -> str:
    """Clean watermarks and ads from subtitle text."""
    return get_stripper().clean_subtitle_text(text)


def should_remove_subtitle(text: str) -> bool:
    """Check if a subtitle block should be removed entirely (pure ad)."""
    return get_stripper().should_remove_subtitle_block(text)
