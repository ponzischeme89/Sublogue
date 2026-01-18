"""
OMDb API client - async movie metadata fetching
Includes:
- Rate limiting (requests / second)
- Concurrency limiting
- Request de-duplication
- Shared aiohttp session
"""

from __future__ import annotations

import asyncio
import aiohttp
import logging
from logging_utils import get_logger
import time
from typing import Dict, Optional

logger = get_logger(__name__)


class RateLimiter:
    """
    Simple async rate limiter (token bucket-ish).
    Limits how often requests may start.
    """

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


class OMDbClient:
    """Async, rate-limited OMDb client"""

    BASE_URL = "https://www.omdbapi.com/"

    def __init__(
        self,
        api_key: str,
        *,
        max_concurrent: int = 5,
        rate_limit_per_sec: float = 2.0,
        db_manager=None,
        timeout: int = 15,
    ):
        self.api_key = api_key
        self.db_manager = db_manager

        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = RateLimiter(rate_limit_per_sec)

        self._session: Optional[aiohttp.ClientSession] = None
        self._inflight: Dict[str, asyncio.Future] = {}

        self._timeout = aiohttp.ClientTimeout(total=timeout)

    # -----------------------------
    # Session management
    # -----------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # -----------------------------
    # Public API
    # -----------------------------

    async def fetch_summary(
        self,
        title: str,
        media_type: str = "movie",
        year: Optional[str] = None,
        season: Optional[int] = None,
        episode: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Fetch summary from OMDb.
        Automatically deduplicates identical in-flight requests.

        Args:
            title: Movie/show title to search
            media_type: "movie" or "series"
            year: Year of release (improves match accuracy)
            season: Season number (for series)
            episode: Episode number (for series)
        """

        key = self._make_cache_key(title, media_type, year, season, episode)

        # Deduplicate in-flight requests
        if key in self._inflight:
            logger.debug("Awaiting inflight OMDb request: %s", key)
            return await self._inflight[key]

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._inflight[key] = future

        try:
            result = await self._fetch_summary_internal(
                title, media_type, year, season, episode
            )
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            self._inflight.pop(key, None)

    async def fetch_summary_by_imdb_id(self, imdb_id: str) -> Optional[dict]:
        """
        Fetch summary from OMDb using a specific IMDb ID.

        Args:
            imdb_id: IMDb ID (e.g., tt1234567)
        """
        if not imdb_id:
            return None

        key = f"imdb:{imdb_id.lower()}"
        if key in self._inflight:
            logger.debug("Awaiting inflight OMDb request: %s", key)
            return await self._inflight[key]

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._inflight[key] = future

        try:
            result = await self._fetch_summary_by_imdb_id_internal(imdb_id)
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            self._inflight.pop(key, None)

    # -----------------------------
    # Internal fetch logic
    # -----------------------------

    async def _fetch_summary_internal(
        self,
        title: str,
        media_type: str,
        year: Optional[str],
        season: Optional[int],
        episode: Optional[int],
    ) -> Optional[dict]:

        logger.info("Fetching OMDb summary for: %s (year=%s)", title, year)

        async with self.semaphore:
            await self.rate_limiter.wait()

            params = {
                "apikey": self.api_key,
                "t": title,
                "plot": "short",
            }

            # Add year for better matching accuracy
            if year:
                params["y"] = year

            if media_type == "series":
                params["type"] = "series"
            if season is not None:
                params["Season"] = season
            if episode is not None:
                params["Episode"] = episode

            session = await self._get_session()
            start = time.monotonic()

            try:
                async with session.get(self.BASE_URL, params=params) as resp:
                    elapsed_ms = int((time.monotonic() - start) * 1000)

                    if resp.status != 200:
                        self._track(False, title, elapsed_ms)
                        logger.error("OMDb HTTP %s for '%s'", resp.status, title)
                        return None

                    data = await resp.json()

                    if data.get("Response") != "True":
                        self._track(False, title, elapsed_ms)
                        logger.warning("OMDb error for '%s': %s", title, data.get("Error"))
                        return None

                    self._track(True, title, elapsed_ms)

                    # Validate year match if year was specified
                    if year:
                        returned_year = data.get("Year", "")
                        # Handle year ranges like "2020-2023" for series
                        if "-" in returned_year:
                            returned_year = returned_year.split("-")[0]
                        if returned_year and returned_year != year:
                            logger.warning(
                                f"Year mismatch for '{title}': requested {year}, got {returned_year} "
                                f"('{data.get('Title')}'). Rejecting result."
                            )
                            return None

                    return self._parse_response(data)

            except asyncio.TimeoutError:
                logger.error("OMDb timeout for '%s'", title)
                return None
            except aiohttp.ClientError as e:
                logger.error("OMDb network error for '%s': %s", title, e)
                return None

    async def _fetch_summary_by_imdb_id_internal(self, imdb_id: str) -> Optional[dict]:
        logger.info("Fetching OMDb summary for IMDb ID: %s", imdb_id)

        async with self.semaphore:
            await self.rate_limiter.wait()

            params = {
                "apikey": self.api_key,
                "i": imdb_id,
                "plot": "short",
            }

            session = await self._get_session()
            start = time.monotonic()

            try:
                async with session.get(self.BASE_URL, params=params) as resp:
                    elapsed_ms = int((time.monotonic() - start) * 1000)

                    if resp.status != 200:
                        self._track(False, imdb_id, elapsed_ms)
                        logger.error("OMDb HTTP %s for IMDb ID '%s'", resp.status, imdb_id)
                        return None

                    data = await resp.json()

                    if data.get("Response") != "True":
                        self._track(False, imdb_id, elapsed_ms)
                        logger.warning("OMDb error for IMDb ID '%s': %s", imdb_id, data.get("Error"))
                        return None

                    self._track(True, imdb_id, elapsed_ms)
                    return self._parse_response(data)

            except asyncio.TimeoutError:
                logger.error("OMDb timeout for IMDb ID '%s'", imdb_id)
                return None
            except aiohttp.ClientError as e:
                logger.error("OMDb network error for IMDb ID '%s': %s", imdb_id, e)
                return None

    # -----------------------------
    # Helpers
    # -----------------------------

    def _parse_response(self, data: dict) -> dict:
        rt_rating = "N/A"
        for r in data.get("Ratings", []):
            if r.get("Source") == "Rotten Tomatoes":
                rt_rating = r.get("Value")
                break

        return {
            "plot": data.get("Plot", "No plot available"),
            "rotten_tomatoes": rt_rating,
            "title": data.get("Title"),
            "year": data.get("Year"),
            "media_type": data.get("Type"),
            "imdb_rating": data.get("imdbRating", "N/A"),
            "runtime": data.get("Runtime", "N/A"),
            # Additional metadata fields
            "director": data.get("Director", "N/A"),
            "actors": data.get("Actors", "N/A"),
            "released": data.get("Released", "N/A"),
            "genre": data.get("Genre", "N/A"),
        }

    def _track(self, success: bool, title: str, response_time_ms: int):
        if not self.db_manager:
            return
        self.db_manager.track_api_call(
            provider="omdb",
            endpoint=f"/?t={title}",
            success=success,
            response_time_ms=response_time_ms,
        )

    @staticmethod
    def _make_cache_key(title, media_type, year, season, episode) -> str:
        return f"{title.lower()}|{media_type}|{year}|{season}|{episode}"
