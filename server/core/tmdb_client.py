"""
TMDb API client - async movie and TV series metadata fetching
"""
import asyncio
import aiohttp
import logging
import time

logging.basicConfig(level=logging.INFO)


class TMDbClient:
    """Async client for The Movie Database (TMDb) API"""

    def __init__(self, api_key, db_manager=None):
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
        self.db_manager = db_manager

    async def search_movie(self, title, year=None, language=None):
        """
        Search for a movie by title

        Args:
            title: Movie title to search
            year: Optional year to narrow search

        Returns:
            dict: Movie data or None if not found
        """
        async with self.semaphore:
            url = f"{self.base_url}/search/movie"
            params = {
                "api_key": self.api_key,
                "query": title
            }
            if year:
                params["year"] = year
            if language:
                params["language"] = language

            try:
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        response_time_ms = int((time.time() - start_time) * 1000)

                        if response.status != 200:
                            logging.error(f"TMDb HTTP error {response.status} for movie '{title}'")
                            # Track failed API call
                            if self.db_manager:
                                self.db_manager.track_api_call(
                                    provider='tmdb',
                                    endpoint='/search/movie',
                                    success=False,
                                    response_time_ms=response_time_ms
                                )
                            return None

                        data = await response.json()

                        if data.get("results") and len(data["results"]) > 0:
                            # Track successful API call
                            if self.db_manager:
                                self.db_manager.track_api_call(
                                    provider='tmdb',
                                    endpoint='/search/movie',
                                    success=True,
                                    response_time_ms=response_time_ms
                                )
                            return data["results"][0]  # Return first match

                        logging.warning(f"No TMDb results for movie '{title}'")
                        # Track failed API call (no results)
                        if self.db_manager:
                            self.db_manager.track_api_call(
                                provider='tmdb',
                                endpoint='/search/movie',
                                success=False,
                                response_time_ms=response_time_ms
                            )
                        return None

            except Exception as e:
                logging.error(f"Error searching TMDb for movie '{title}': {e}")
                return None

    async def search_tv(self, title, year=None, language=None):
        """
        Search for a TV series by title

        Args:
            title: TV series title to search
            year: Optional year to narrow search

        Returns:
            dict: TV series data or None if not found
        """
        async with self.semaphore:
            url = f"{self.base_url}/search/tv"
            params = {
                "api_key": self.api_key,
                "query": title
            }
            if year:
                params["first_air_date_year"] = year
            if language:
                params["language"] = language

            try:
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        response_time_ms = int((time.time() - start_time) * 1000)

                        if response.status != 200:
                            logging.error(f"TMDb HTTP error {response.status} for TV '{title}'")
                            # Track failed API call
                            if self.db_manager:
                                self.db_manager.track_api_call(
                                    provider='tmdb',
                                    endpoint='/search/tv',
                                    success=False,
                                    response_time_ms=response_time_ms
                                )
                            return None

                        data = await response.json()

                        if data.get("results") and len(data["results"]) > 0:
                            # Track successful API call
                            if self.db_manager:
                                self.db_manager.track_api_call(
                                    provider='tmdb',
                                    endpoint='/search/tv',
                                    success=True,
                                    response_time_ms=response_time_ms
                                )
                            return data["results"][0]  # Return first match

                        logging.warning(f"No TMDb results for TV series '{title}'")
                        # Track failed API call (no results)
                        if self.db_manager:
                            self.db_manager.track_api_call(
                                provider='tmdb',
                                endpoint='/search/tv',
                                success=False,
                                response_time_ms=response_time_ms
                            )
                        return None

            except Exception as e:
                logging.error(f"Error searching TMDb for TV '{title}': {e}")
                return None

    async def get_movie_details(self, movie_id, language=None):
        """
        Get detailed movie information

        Args:
            movie_id: TMDb movie ID

        Returns:
            dict: Detailed movie data
        """
        async with self.semaphore:
            url = f"{self.base_url}/movie/{movie_id}"
            params = {"api_key": self.api_key}
            if language:
                params["language"] = language

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status != 200:
                            logging.error(f"TMDb HTTP error {response.status} for movie ID {movie_id}")
                            return None

                        return await response.json()

            except Exception as e:
                logging.error(f"Error getting TMDb movie details for ID {movie_id}: {e}")
                return None

    async def get_tv_details(self, tv_id, language=None):
        """
        Get detailed TV series information

        Args:
            tv_id: TMDb TV series ID

        Returns:
            dict: Detailed TV series data
        """
        async with self.semaphore:
            url = f"{self.base_url}/tv/{tv_id}"
            params = {"api_key": self.api_key}
            if language:
                params["language"] = language

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status != 200:
                            logging.error(f"TMDb HTTP error {response.status} for TV ID {tv_id}")
                            return None

                        return await response.json()

            except Exception as e:
                logging.error(f"Error getting TMDb TV details for ID {tv_id}: {e}")
                return None

    async def get_tv_season(self, tv_id, season_number, language=None):
        """
        Get TV season information

        Args:
            tv_id: TMDb TV series ID
            season_number: Season number

        Returns:
            dict: Season data including episodes
        """
        async with self.semaphore:
            url = f"{self.base_url}/tv/{tv_id}/season/{season_number}"
            params = {"api_key": self.api_key}
            if language:
                params["language"] = language

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status != 200:
                            logging.error(f"TMDb HTTP error {response.status} for TV {tv_id} season {season_number}")
                            return None

                        return await response.json()

            except Exception as e:
                logging.error(f"Error getting TMDb season data: {e}")
                return None

    async def fetch_summary(self, title, media_type="movie", year=None, season=None, episode=None, language=None):
        """
        Fetch summary for movie or TV series

        Args:
            title: Title to search
            media_type: "movie" or "tv"
            year: Optional year
            season: Optional season number (for TV)
            episode: Optional episode number (for TV)

        Returns:
            dict: {plot, title, year, media_type, rating} or None if not found
        """
        logging.info(f"Fetching TMDb summary for: {title} (type: {media_type})")

        try:
            if media_type == "tv":
                # Search for TV series
                search_result = await self.search_tv(title, year, language=language)
                if not search_result:
                    return None

                tv_id = search_result["id"]

                # Get detailed TV info
                tv_details = await self.get_tv_details(tv_id, language=language)
                if not tv_details:
                    return None

                plot = tv_details.get("overview", "No plot available")

                # If specific season/episode requested, try to get that plot
                if season is not None:
                    season_data = await self.get_tv_season(tv_id, season, language=language)
                    if season_data and episode is not None:
                        episodes = season_data.get("episodes", [])
                        for ep in episodes:
                            if ep.get("episode_number") == episode:
                                plot = ep.get("overview", plot)
                                break

                # Get episode runtime (usually consistent across series)
                runtime = "N/A"
                episode_run_time = tv_details.get("episode_run_time", [])
                if episode_run_time and len(episode_run_time) > 0:
                    runtime = f"{episode_run_time[0]} min"

                return {
                    "plot": plot,
                    "title": tv_details.get("name", title),
                    "year": tv_details.get("first_air_date", "")[:4] if tv_details.get("first_air_date") else "N/A",
                    "media_type": "tv",
                    "rating": f"{tv_details.get('vote_average', 0):.1f}/10",
                    "runtime": runtime
                }

            else:  # movie
                # Search for movie
                search_result = await self.search_movie(title, year, language=language)
                if not search_result:
                    return None

                movie_id = search_result["id"]

                # Get detailed movie info
                movie_details = await self.get_movie_details(movie_id, language=language)
                if not movie_details:
                    return None

                # Get runtime
                runtime = "N/A"
                if movie_details.get("runtime"):
                    runtime = f"{movie_details.get('runtime')} min"

                return {
                    "plot": movie_details.get("overview", "No plot available"),
                    "title": movie_details.get("title", title),
                    "year": movie_details.get("release_date", "")[:4] if movie_details.get("release_date") else "N/A",
                    "media_type": "movie",
                    "rating": f"{movie_details.get('vote_average', 0):.1f}/10",
                    "runtime": runtime
                }

        except Exception as e:
            logging.error(f"Error fetching TMDb summary for '{title}': {e}")
            return None
