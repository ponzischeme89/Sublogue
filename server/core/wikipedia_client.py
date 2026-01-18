"""
Wikipedia API client - strict metadata fetching

Uses the MediaWiki search API and REST summary endpoint.
Strict matching avoids false positives by requiring:
- exact base title match (after normalization)
- year match when provided
- media type hints (film vs TV series)
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Dict, List, Optional

import aiohttp

from logging_utils import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Simple async rate limiter."""

    def __init__(self, rate_per_second: float):
        self._interval = 1.0 / rate_per_second
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def wait(self):
        async with self._lock:
            now = time.monotonic()
            delta = now - self._last_call
            if delta < self._interval:
                await asyncio.sleep(self._interval - delta)
            self._last_call = time.monotonic()


class WikipediaClient:
    """Async, strict Wikipedia client."""

    API_URL = "https://en.wikipedia.org/w/api.php"
    SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

    def __init__(
        self,
        *,
        max_concurrent: int = 4,
        rate_limit_per_sec: float = 2.0,
        db_manager=None,
        timeout: int = 15,
    ):
        self.db_manager = db_manager
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = RateLimiter(rate_limit_per_sec)
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_summary(
        self,
        title: str,
        *,
        year: Optional[str] = None,
        is_series: bool = False,
        season: Optional[int] = None,
        episode: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Fetch a strict Wikipedia summary match for a title.

        Wikipedia does not provide episode-level summaries in a structured way.
        If season/episode is provided, return None to avoid incorrect matches.
        """
        if season is not None or episode is not None:
            return None

        matches = await self.search_titles(
            title,
            year=year,
            is_series=is_series,
            max_results=1,
        )
        return matches[0] if matches else None

    async def search_titles(
        self,
        title: str,
        *,
        year: Optional[str] = None,
        is_series: bool = False,
        max_results: int = 5,
    ) -> List[dict]:
        """Search Wikipedia with strict filtering and return summary results."""
        if not title:
            return []

        async with self.semaphore:
            await self.rate_limiter.wait()

            query = f'intitle:"{title}"'
            if year:
                query = f'{query} {year}'
            if is_series:
                query = f"{query} television series"
            else:
                query = f"{query} film"

            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": max_results * 2,
                "format": "json",
            }

            session = await self._get_session()
            start = time.monotonic()

            try:
                async with session.get(self.API_URL, params=params) as resp:
                    elapsed_ms = int((time.monotonic() - start) * 1000)
                    if resp.status != 200:
                        self._track(False, "/w/api.php", elapsed_ms)
                        return []
                    data = await resp.json()
                    self._track(True, "/w/api.php", elapsed_ms)
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                logger.error("Wikipedia search error for '%s': %s", title, e)
                return []

            search_results = data.get("query", {}).get("search", [])
            if not search_results:
                return []

            results: List[dict] = []
            for item in search_results:
                page_title = item.get("title")
                if not page_title:
                    continue

                summary = await self._fetch_summary_for_title(page_title)
                if not summary:
                    continue

                description = summary.get("description") or ""
                extract = summary.get("extract") or ""

                if not self._is_strict_match(
                    title,
                    page_title,
                    year=year,
                    is_series=is_series,
                    description=description,
                    extract=extract,
                ):
                    continue

                results.append(self._build_result(summary, is_series))
                if len(results) >= max_results:
                    break

            return results

    async def _fetch_summary_for_title(self, title: str) -> Optional[dict]:
        session = await self._get_session()
        url = self.SUMMARY_URL.format(title=aiohttp.helpers.quote(title, safe=""))
        start = time.monotonic()

        try:
            async with session.get(url) as resp:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                if resp.status != 200:
                    self._track(False, "/page/summary", elapsed_ms)
                    return None
                data = await resp.json()
                self._track(True, "/page/summary", elapsed_ms)
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.error("Wikipedia summary error for '%s': %s", title, e)
            return None

        # Skip disambiguation and empty extracts
        if data.get("type") == "disambiguation":
            return None
        if not data.get("extract"):
            return None
        return data

    def _build_result(self, summary: dict, is_series: bool) -> dict:
        title = summary.get("title")
        description = summary.get("description") or ""
        extract = summary.get("extract") or "No plot available"
        year = self._extract_year(summary.get("title", ""), description, extract)
        poster = None
        thumbnail = summary.get("thumbnail") or {}
        if isinstance(thumbnail, dict):
            poster = thumbnail.get("source")

        return {
            "plot": extract,
            "title": title,
            "year": year or "N/A",
            "media_type": "series" if is_series else "movie",
            "imdb_rating": "N/A",
            "runtime": "N/A",
            "poster": poster,
            "imdb_id": None,
            "director": "N/A",
            "actors": "N/A",
            "released": "N/A",
            "genre": description or "N/A",
        }

    def _is_strict_match(
        self,
        query_title: str,
        page_title: str,
        *,
        year: Optional[str],
        is_series: bool,
        description: str,
        extract: str,
    ) -> bool:
        query_base = self._normalize_title(query_title)
        page_base = self._normalize_title(self._strip_parenthetical(page_title))
        if query_base != page_base:
            return False

        text = f"{description} {extract}".lower()
        if year:
            if year not in page_title and not re.search(rf"\\b{re.escape(year)}\\b", text):
                return False

        if is_series:
            if "television series" not in text and "tv series" not in text and "miniseries" not in text:
                return False
        else:
            if "film" not in text and "movie" not in text:
                return False

        if "disambiguation" in text:
            return False

        return True

    @staticmethod
    def _strip_parenthetical(title: str) -> str:
        return re.sub(r"\s*\(.*?\)\s*$", "", title or "")

    @staticmethod
    def _normalize_title(title: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", title.lower())
        return " ".join(normalized.split())

    @staticmethod
    def _extract_year(title: str, description: str, extract: str) -> Optional[str]:
        title_match = re.search(r"\b(19|20)\d{2}\b", title or "")
        if title_match:
            return title_match.group(0)
        text = f"{description} {extract}"
        match = re.search(r"\b(19|20)\d{2}\b", text)
        return match.group(0) if match else None

    def _track(self, success: bool, endpoint: str, response_time_ms: int):
        if not self.db_manager:
            return
        self.db_manager.track_api_call(
            provider="wikipedia",
            endpoint=endpoint,
            success=success,
            response_time_ms=response_time_ms,
            call_count=1,
        )
