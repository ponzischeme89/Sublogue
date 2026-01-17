"""
TVmaze API client - async TV metadata fetching
"""
import aiohttp
import logging
import re
import time

logger = logging.getLogger(__name__)


class TVMazeClient:
    """Async client for the TVmaze API (no API key required)."""

    BASE_URL = "https://api.tvmaze.com"

    def __init__(self, db_manager=None, timeout=15):
        self.db_manager = db_manager
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def fetch_summary(self, title, year=None, season=None, episode=None):
        """
        Fetch summary for a TV series (optionally episode-specific).

        Args:
            title: Series title to search
            year: Optional year to validate match
            season: Optional season number
            episode: Optional episode number
        """
        show = await self._fetch_show(title, year)
        if not show:
            return None

        plot = self._strip_html(show.get("summary")) or "No plot available"

        if season is not None and episode is not None:
            episode_data = await self._fetch_episode(show.get("id"), season, episode)
            if episode_data:
                episode_summary = self._strip_html(episode_data.get("summary"))
                if episode_summary:
                    plot = episode_summary

        rating = show.get("rating", {}).get("average")
        imdb_rating = f"{rating:.1f}" if isinstance(rating, (int, float)) else "N/A"

        runtime_value = show.get("runtime") or show.get("averageRuntime")
        runtime = f"{runtime_value} min" if runtime_value else "N/A"

        premiered = show.get("premiered") or ""
        year_value = premiered[:4] if premiered else "N/A"

        return {
            "plot": plot,
            "title": show.get("name", title),
            "year": year_value,
            "media_type": "tv",
            "imdb_rating": imdb_rating,
            "rotten_tomatoes": "N/A",
            "runtime": runtime,
        }

    async def _fetch_show(self, title, year):
        params = {"q": title}
        url = f"{self.BASE_URL}/singlesearch/shows"

        start_time = time.time()
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.get(url, params=params) as response:
                    response_time_ms = int((time.time() - start_time) * 1000)

                    if response.status != 200:
                        self._track(False, "/singlesearch/shows", response_time_ms)
                        logger.error("TVmaze HTTP %s for '%s'", response.status, title)
                        return None

                    data = await response.json()
                    self._track(True, "/singlesearch/shows", response_time_ms)

                    if year:
                        premiered = data.get("premiered") or ""
                        if premiered and premiered[:4] != year:
                            logger.warning(
                                "TVmaze year mismatch for '%s': requested %s, got %s",
                                title,
                                year,
                                premiered[:4],
                            )
                            return None

                    return data
        except Exception as e:
            logger.error("TVmaze error for '%s': %s", title, e)
            return None

    async def _fetch_episode(self, show_id, season, episode):
        if not show_id:
            return None

        params = {"season": season, "number": episode}
        url = f"{self.BASE_URL}/shows/{show_id}/episodebynumber"

        start_time = time.time()
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.get(url, params=params) as response:
                    response_time_ms = int((time.time() - start_time) * 1000)

                    if response.status != 200:
                        self._track(False, "/shows/{id}/episodebynumber", response_time_ms)
                        return None

                    data = await response.json()
                    self._track(True, "/shows/{id}/episodebynumber", response_time_ms)
                    return data
        except Exception as e:
            logger.error("TVmaze episode error for show %s: %s", show_id, e)
            return None

    def _track(self, success, endpoint, response_time_ms):
        if not self.db_manager:
            return
        self.db_manager.track_api_call(
            provider="tvmaze",
            endpoint=endpoint,
            success=success,
            response_time_ms=response_time_ms,
        )

    @staticmethod
    def _strip_html(text):
        if not text:
            return ""
        return re.sub(r"<[^>]+>", "", text).strip()
