import asyncio
import json
import os
import threading
import time
import re
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

from core.config_manager import ConfigManager
from core.omdb_client import OMDbClient
from core.tmdb_client import TMDbClient
from core.tvmaze_client import TVMazeClient
from core.subtitle_processor import SubtitleProcessor, SubtitleFormatOptions, SUBLOGUE_TOKEN_PATTERN, SUBLOGUE_SENTINEL
from core.keyword_stripper import get_stripper
from core.file_scanner import FileScanner
from core.database import DatabaseManager
from logging_utils import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Initialize Flask app with static folder for production
static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app = Flask(__name__, static_folder=static_folder, static_url_path='')
CORS(app)

# Global instances
config = ConfigManager()
db = DatabaseManager()
omdb_client = None
tmdb_client = None
tvmaze_client = None
processor = None

# In-memory scan state (still used for current session)
scan_state = {
    "files": [],
    "scanning": False,
    "last_scan": None
}

scheduled_scan_thread = None
scheduled_scan_stop = threading.Event()


def parse_iso_datetime(value):
    """Parse ISO datetime strings into naive UTC datetime."""
    if not value or not isinstance(value, str):
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def perform_scheduled_scan(directory):
    """Run a scheduled scan without mutating in-memory scan state."""
    start_time = time.time()
    files = []

    for batch in FileScanner.scan_directory(directory, batch_size=10):
        files.extend(batch)

    scan_duration_ms = int((time.time() - start_time) * 1000)
    files_with_plot = sum(1 for f in files if f.get("has_plot", False))

    scan_id = db.add_scan_history(
        directory=directory,
        files_found=len(files),
        files_with_plot=files_with_plot,
        scan_duration_ms=scan_duration_ms
    )
    db.add_scan_files(scan_id, files)

    return {
        "files_found": len(files),
        "files_with_plot": files_with_plot,
        "scan_duration_ms": scan_duration_ms
    }


def scheduled_scan_worker():
    """Background worker to execute scheduled scans."""
    while not scheduled_scan_stop.is_set():
        try:
            now = datetime.utcnow()
            due_scan_ids = db.get_due_scheduled_scans(now)
            for scan_id in due_scan_ids:
                scan = db.get_scheduled_scan(scan_id)
                if not scan:
                    continue
                if not db.mark_scheduled_scan_running(scan_id, started_at=datetime.utcnow()):
                    continue
                try:
                    result = perform_scheduled_scan(scan["directory"])
                    db.complete_scheduled_scan(
                        scan_id,
                        result["files_found"],
                        result["files_with_plot"],
                        result["scan_duration_ms"]
                    )
                except Exception as e:
                    logger.error(f"Scheduled scan failed: {e}")
                    db.fail_scheduled_scan(scan_id, str(e))
        except Exception as e:
            logger.error(f"Scheduled scan worker error: {e}")
        scheduled_scan_stop.wait(5)


def start_scheduled_scan_worker():
    """Start the scheduled scan worker thread once."""
    global scheduled_scan_thread
    if scheduled_scan_thread and scheduled_scan_thread.is_alive():
        return
    scheduled_scan_thread = threading.Thread(target=scheduled_scan_worker, daemon=True)
    scheduled_scan_thread.start()


def initialize_clients():
    """Initialize OMDb, TMDb, TVmaze clients and processor with current API keys"""
    global omdb_client, tmdb_client, tvmaze_client, processor

    # Load OMDb API key
    omdb_key = _get_str_setting("omdb_api_key", "")
    if not omdb_key:
        # Fallback to legacy "api_key" setting
        omdb_key = _get_str_setting("api_key", "")
    if not omdb_key:
        omdb_key = config.get("api_key", "")

    # Load TMDb API key
    tmdb_key = _get_str_setting("tmdb_api_key", "")
    omdb_enabled = _get_bool_setting("omdb_enabled", False)
    tmdb_enabled = _get_bool_setting("tmdb_enabled", False)
    tvmaze_enabled = _get_bool_setting("tvmaze_enabled", False)
    preferred_source = _get_str_setting("preferred_source", "omdb")

    # Initialize clients with db_manager for usage tracking
    if omdb_enabled and omdb_key:
        omdb_client = OMDbClient(omdb_key, db_manager=db)
        logger.info("OMDb client initialized with usage tracking")
    else:
        logger.warning("No OMDb API key configured")

    if tmdb_enabled and tmdb_key:
        tmdb_client = TMDbClient(tmdb_key, db_manager=db)
        logger.info("TMDb client initialized with usage tracking")
    else:
        logger.info("No TMDb API key configured")

    if tvmaze_enabled:
        tvmaze_client = TVMazeClient(db_manager=db)
        logger.info("TVmaze client initialized with usage tracking")
    else:
        tvmaze_client = None
        logger.info("TVmaze integration disabled")

    # Initialize processor with available clients
    if omdb_client or tmdb_client or tvmaze_client:
        processor = SubtitleProcessor(
            omdb_client,
            tmdb_client,
            tvmaze_client,
            preferred_source=preferred_source,
        )
        logger.info("Processor initialized")
    else:
        logger.warning("No metadata providers configured")


# Migrate existing settings to database on startup
def migrate_settings():
    """Migrate settings from JSON file to database"""
    try:
        # Check if settings exist in database
        db_settings = db.get_all_settings()

        # If database is empty, migrate from config file
        if not db_settings:
            logger.info("Migrating settings from config file to database")
            file_settings = config.get_all()
            for key, value in file_settings.items():
                db.set_setting(key, value)
            logger.info("Settings migration complete")
    except Exception as e:
        logger.error(f"Error migrating settings: {e}")


def _get_bool_setting(key: str, default: bool) -> bool:
    """Fetch a boolean setting with explicit casting for type safety."""
    value = db.get_setting(key, default)
    return bool(value)

def _get_str_setting(key: str, default: str) -> str:
    """Fetch a string setting with explicit casting for type safety."""
    value = db.get_setting(key, default)
    if value is None:
        return default
    return str(value)

def _get_folder_rule_for_path(file_path: str, rules: list[dict]) -> dict | None:
    """Pick the most specific folder rule that matches the file path."""
    if not rules:
        return None
    normalized_file = os.path.normcase(os.path.abspath(file_path))
    best_rule = None
    best_len = -1
    for rule in rules:
        directory = rule.get("directory")
        if not directory:
            continue
        normalized_dir = os.path.normcase(os.path.abspath(directory))
        normalized_dir = normalized_dir.rstrip(os.sep)
        prefix = normalized_dir + os.sep
        if normalized_file == normalized_dir or normalized_file.startswith(prefix):
            if len(normalized_dir) > best_len:
                best_len = len(normalized_dir)
                best_rule = rule
    return best_rule


def _merge_format_options(base_options: SubtitleFormatOptions, rule: dict | None) -> SubtitleFormatOptions:
    """Merge folder rule overrides into format options."""
    if not rule:
        return base_options
    def _override_bool(key: str, current: bool) -> bool:
        value = rule.get(key)
        return current if value is None else bool(value)
    return SubtitleFormatOptions(
        title_bold=_override_bool("subtitle_title_bold", base_options.title_bold),
        plot_italic=_override_bool("subtitle_plot_italic", base_options.plot_italic),
        show_director=_override_bool("subtitle_show_director", base_options.show_director),
        show_actors=_override_bool("subtitle_show_actors", base_options.show_actors),
        show_released=_override_bool("subtitle_show_released", base_options.show_released),
        show_genre=_override_bool("subtitle_show_genre", base_options.show_genre),
    )


def _parse_library_identity(file_info: dict) -> dict:
    """Parse title, year, season, and episode from filename metadata."""
    file_name = file_info.get("name", "")
    title = file_info.get("title")
    year = file_info.get("year")

    if not title:
        stripped = get_stripper().clean_filename(file_name, preserve_year=True)
        title = stripped.get("cleaned_title") or Path(file_name).stem
        year = year or stripped.get("year")
        season = stripped.get("season")
        episode = stripped.get("episode")
    else:
        season, episode = get_stripper().extract_season_episode(file_name)

    clean_title = title or Path(file_name).stem
    clean_title = clean_title.replace(SUBLOGUE_SENTINEL, "")
    clean_title = re.sub(r"<[^>]+>", "", clean_title)
    clean_title = SUBLOGUE_TOKEN_PATTERN.sub("", clean_title)
    clean_title = re.sub(r"\b(en|eng|english|ita|it|italian|fr|es|de|multi)\b", "", clean_title, flags=re.I)
    clean_title = re.sub(r'\s*-\s*copy\b', '', clean_title, flags=re.I)
    clean_title = re.sub(r'\s*copy\b', '', clean_title, flags=re.I)
    clean_title = re.sub(r"\((\d{4})\)\s*\(\1\)", r"(\1)", clean_title)
    if year:
        clean_title = re.sub(rf"\s*\({re.escape(str(year))}\)$", "", clean_title)
    clean_title = " ".join(clean_title.split()).strip()

    return {
        "title": clean_title,
        "year": year,
        "season": season,
        "episode": episode,
    }


def _group_key(title: str, year: str | None) -> str:
    base = title.strip().lower()
    return f"{base} ({year})" if year else base


def _build_library_items(files: list[dict], latest_results: dict, limit: int | None) -> list[dict]:
    """Aggregate scan files into library items."""
    grouped = {}
    for file_info in files:
        parsed = _parse_library_identity(file_info)
        key = _group_key(parsed["title"], parsed["year"])
        item = grouped.get(key)
        if not item:
            # Try fuzzy match to existing groups
            for existing_key, existing in grouped.items():
                ratio = SequenceMatcher(None, existing["title"].lower(), parsed["title"].lower()).ratio()
                if ratio >= 0.88:
                    key = existing_key
                    item = existing
                    break
        if not item:
            item = grouped.setdefault(key, {
                "title": parsed["title"],
                "year": parsed["year"],
            "files": [],
            "health": {
                "missing_plot": 0,
                "duplicate_plot": 0,
                "insufficient_gap": 0
            }
        })

        issues = []
        if not file_info.get("has_plot"):
            issues.append({"type": "missing_plot", "reason": "No plot detected"})
            item["health"]["missing_plot"] += 1
        if (file_info.get("plot_marker_count") or 0) > 1:
            issues.append({"type": "duplicate_plot", "reason": "Multiple plot markers detected"})
            item["health"]["duplicate_plot"] += 1

        latest_result = latest_results.get(file_info.get("path"))
        if latest_result and latest_result.get("status") == "Insufficient Gap":
            issues.append({
                "type": "insufficient_gap",
                "reason": latest_result.get("error_message") or "Insufficient gap before first subtitle"
            })
            item["health"]["insufficient_gap"] += 1

        display_name = parsed["title"]
        if parsed["season"] is not None and parsed["episode"] is not None:
            display_name = f"{parsed['title']} - S{parsed['season']:02d}E{parsed['episode']:02d}"
        elif parsed["year"]:
            display_name = f"{parsed['title']} ({parsed['year']})"

        item["files"].append({
            **file_info,
            "display_name": display_name,
            "duplicate_plot": (file_info.get("plot_marker_count") or 0) > 1,
            "latest_status": latest_result.get("status") if latest_result else None,
            "latest_error": latest_result.get("error_message") if latest_result else None,
            "issues": issues
        })

    items = list(grouped.values())
    items.sort(
        key=lambda entry: (
            entry["health"]["missing_plot"]
            + entry["health"]["duplicate_plot"]
            + entry["health"]["insufficient_gap"]
        ),
        reverse=True
    )
    if limit is None:
        return items
    return items[:limit]

def get_format_options_from_settings() -> SubtitleFormatOptions:
    """Load subtitle formatting options from database settings."""
    return SubtitleFormatOptions(
        title_bold=_get_bool_setting("subtitle_title_bold", True),
        plot_italic=_get_bool_setting("subtitle_plot_italic", True),
        show_director=_get_bool_setting("subtitle_show_director", False),
        show_actors=_get_bool_setting("subtitle_show_actors", False),
        show_released=_get_bool_setting("subtitle_show_released", False),
        show_genre=_get_bool_setting("subtitle_show_genre", False),
    )


# Initialize on startup
migrate_settings()
initialize_clients()


# ============ SETTINGS ENDPOINTS ============

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current application settings"""
    settings = db.get_all_settings()

    # Ensure default values
    if "omdb_api_key" not in settings:
        # Check legacy api_key
        settings["omdb_api_key"] = settings.get("api_key", "")
    if "tmdb_api_key" not in settings:
        settings["tmdb_api_key"] = ""
    if "default_directory" not in settings:
        settings["default_directory"] = ""
    if "duration" not in settings:
        settings["duration"] = 40
    if "preferred_source" not in settings:
        settings["preferred_source"] = "omdb"  # omdb, tmdb, tvmaze, or both
    if "insertion_position" not in settings:
        settings["insertion_position"] = "start"  # start, end, or index
    if "strip_keywords" not in settings:
        settings["strip_keywords"] = True
    if "clean_subtitle_content" not in settings:
        settings["clean_subtitle_content"] = True
    if "omdb_enabled" not in settings:
        settings["omdb_enabled"] = False
    if "tmdb_enabled" not in settings:
        settings["tmdb_enabled"] = False
    if "tvmaze_enabled" not in settings:
        settings["tvmaze_enabled"] = False

    # Subtitle formatting settings
    if "subtitle_title_bold" not in settings:
        settings["subtitle_title_bold"] = True  # Bold the movie title
    if "subtitle_plot_italic" not in settings:
        settings["subtitle_plot_italic"] = True  # Italicize the plot text
    if "subtitle_show_director" not in settings:
        settings["subtitle_show_director"] = False  # Show director in header
    if "subtitle_show_actors" not in settings:
        settings["subtitle_show_actors"] = False  # Show actors in header
    if "subtitle_show_released" not in settings:
        settings["subtitle_show_released"] = False  # Show release date in header
    if "subtitle_show_genre" not in settings:
        settings["subtitle_show_genre"] = False  # Show genre in header

    # UI settings
    if "quote_style" not in settings:
        settings["quote_style"] = "sarcastic"  # sarcastic, rude, or nice

    return jsonify(settings)


@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update application settings"""
    try:
        data = request.json

        # Update settings in database
        if "omdb_api_key" in data:
            db.set_setting("omdb_api_key", data["omdb_api_key"])
        if "tmdb_api_key" in data:
            db.set_setting("tmdb_api_key", data["tmdb_api_key"])
        if "api_key" in data:
            # Legacy support
            db.set_setting("omdb_api_key", data["api_key"])
        if "default_directory" in data:
            db.set_setting("default_directory", data["default_directory"])
        if "duration" in data:
            db.set_setting("duration", int(data["duration"]))
        if "preferred_source" in data:
            db.set_setting("preferred_source", data["preferred_source"])
        if "insertion_position" in data:
            db.set_setting("insertion_position", data["insertion_position"])
        if "strip_keywords" in data:
            db.set_setting("strip_keywords", bool(data["strip_keywords"]))
        if "clean_subtitle_content" in data:
            db.set_setting("clean_subtitle_content", bool(data["clean_subtitle_content"]))
        if "omdb_enabled" in data:
            db.set_setting("omdb_enabled", bool(data["omdb_enabled"]))
        if "tmdb_enabled" in data:
            db.set_setting("tmdb_enabled", bool(data["tmdb_enabled"]))
        if "tvmaze_enabled" in data:
            db.set_setting("tvmaze_enabled", bool(data["tvmaze_enabled"]))

        # Subtitle formatting settings
        if "subtitle_title_bold" in data:
            db.set_setting("subtitle_title_bold", bool(data["subtitle_title_bold"]))
        if "subtitle_plot_italic" in data:
            db.set_setting("subtitle_plot_italic", bool(data["subtitle_plot_italic"]))
        if "subtitle_show_director" in data:
            db.set_setting("subtitle_show_director", bool(data["subtitle_show_director"]))
        if "subtitle_show_actors" in data:
            db.set_setting("subtitle_show_actors", bool(data["subtitle_show_actors"]))
        if "subtitle_show_released" in data:
            db.set_setting("subtitle_show_released", bool(data["subtitle_show_released"]))
        if "subtitle_show_genre" in data:
            db.set_setting("subtitle_show_genre", bool(data["subtitle_show_genre"]))

        # UI settings
        if "quote_style" in data:
            db.set_setting("quote_style", data["quote_style"])

        # Reinitialize clients with new API keys
        initialize_clients()

        return jsonify({
            "success": True,
            "message": "Settings saved successfully"
        })

    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============ SCAN ENDPOINTS ============

@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    """Start scanning directory for SRT files"""
    try:
        data = request.json
        directory = data.get("directory", db.get_setting("default_directory", ""))

        if not directory:
            return jsonify({
                "success": False,
                "error": "No directory specified"
            }), 400

        # CRITICAL: Reset scan state before starting to ensure clean slate
        scan_state["files"] = []
        scan_state["scanning"] = True
        scan_state["last_scan"] = None
        start_time = time.time()

        logger.info(f"Starting fresh scan of directory: {directory}")

        # Perform scan - collect batches into a flat list
        files = []
        for batch in FileScanner.scan_directory(directory, batch_size=10):
            files.extend(batch)

        # Calculate scan duration
        scan_duration_ms = int((time.time() - start_time) * 1000)

        # Count files with plot
        files_with_plot = sum(1 for f in files if f.get("has_plot", False))

        # Save scan history to database
        scan_id = db.add_scan_history(
            directory=directory,
            files_found=len(files),
            files_with_plot=files_with_plot,
            scan_duration_ms=scan_duration_ms
        )
        db.add_scan_files(scan_id, files)

        # Load existing suggested matches for this directory
        suggested_matches = db.get_suggested_matches_for_directory(directory)

        # Enrich files with suggested matches
        for file in files:
            file_path = file.get("path")
            if file_path in suggested_matches:
                file["suggested_match"] = suggested_matches[file_path]

        # Update state with fresh data
        scan_state["files"] = files
        scan_state["scanning"] = False
        scan_state["last_scan"] = datetime.now().isoformat()

        logger.info(f"Scan completed: {len(files)} files found, {len(suggested_matches)} suggested matches loaded")

        return jsonify({
            "success": True,
            "count": len(files),
            "files": files,
            "suggested_matches": suggested_matches
        })

    except ValueError as e:
        scan_state["scanning"] = False
        logger.error(f"Invalid directory: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except Exception as e:
        scan_state["scanning"] = False
        logger.error(f"Scan error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/scan/stream', methods=['POST'])
def stream_scan():
    """Stream scanning progress using Server-Sent Events"""
    try:
        data = request.json
        directory = data.get("directory", db.get_setting("default_directory", ""))

        if not directory:
            return jsonify({
                "success": False,
                "error": "No directory specified"
            }), 400

        client_closed = threading.Event()

        def generate():
            """Generator function that yields SSE-formatted progress updates"""
            try:
                # Reset scan state
                scan_state["files"] = []
                scan_state["scanning"] = True
                scan_state["last_scan"] = None
                start_time = time.time()

                logger.info(f"Starting streaming scan of directory: {directory}")

                # Send initial status
                try:
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Starting scan...', 'filesFound': 0})}\n\n"
                except GeneratorExit:
                    logger.info("Client disconnected at start, stopping scan")
                    scan_state["scanning"] = False
                    return

                all_files = []
                batch_count = 0

                # Stream batches as they're found
                for batch in FileScanner.scan_directory(directory, batch_size=10):
                    if client_closed.is_set():
                        logger.info("Client disconnected, stopping scan loop")
                        scan_state["scanning"] = False
                        return
                    # Check if client is still connected before processing
                    try:
                        batch_count += 1
                        all_files.extend(batch)

                        # Send progress update
                        progress_data = {
                            'type': 'progress',
                            'message': f'Scanning... found {len(all_files)} files',
                            'filesFound': len(all_files),
                            'batch': batch,
                            'batchNumber': batch_count
                        }
                        yield f"data: {json.dumps(progress_data)}\n\n"
                    except GeneratorExit:
                        # Client disconnected, stop scanning
                        logger.info(f"Client disconnected during scan. Stopping at {len(all_files)} files.")
                        scan_state["scanning"] = False
                        return

                # Calculate scan duration
                scan_duration_ms = int((time.time() - start_time) * 1000)

                # Count files with plot
                files_with_plot = sum(1 for f in all_files if f.get("has_plot", False))

                # Save scan history to database
                scan_id = db.add_scan_history(
                    directory=directory,
                    files_found=len(all_files),
                    files_with_plot=files_with_plot,
                    scan_duration_ms=scan_duration_ms
                )
                db.add_scan_files(scan_id, all_files)

                # Load existing suggested matches
                logger.info("Loading suggested matches from database...")
                try:
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Loading saved matches...', 'filesFound': len(all_files)})}\n\n"
                except GeneratorExit:
                    logger.info("Client disconnected before loading matches")
                    scan_state["scanning"] = False
                    return

                suggested_matches = db.get_suggested_matches_for_directory(directory)

                # Enrich files with suggested matches
                for file in all_files:
                    file_path = file.get("path")
                    if file_path in suggested_matches:
                        file["suggested_match"] = suggested_matches[file_path]

                # Update state
                scan_state["files"] = all_files
                scan_state["scanning"] = False
                scan_state["last_scan"] = datetime.now().isoformat()

                logger.info(f"Scan completed: {len(all_files)} files found, {len(suggested_matches)} suggested matches loaded")

                # Send completion event
                try:
                    completion_data = {
                        'type': 'complete',
                        'success': True,
                        'count': len(all_files),
                        'filesWithPlot': files_with_plot,
                        'duration': scan_duration_ms,
                        'files': all_files,
                        'suggested_matches': suggested_matches
                    }
                    yield f"data: {json.dumps(completion_data)}\n\n"
                except GeneratorExit:
                    logger.info("Client disconnected before completion message")
                    return

            except Exception as e:
                scan_state["scanning"] = False
                logger.error(f"Streaming scan error: {e}")
                error_data = {
                    'type': 'error',
                    'error': str(e)
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        response = Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive'
            }
        )
        response.call_on_close(client_closed.set)
        return response

    except Exception as e:
        logger.error(f"Stream scan setup error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/scan/status', methods=['GET'])
def get_scan_status():
    """Get current scan status and results"""
    return jsonify({
        "scanning": scan_state["scanning"],
        "last_scan": scan_state["last_scan"],
        "file_count": len(scan_state["files"]),
        "files": scan_state["files"]
    })


@app.route('/api/scheduled-scans', methods=['GET'])
def get_scheduled_scans():
    """Get scheduled scans"""
    try:
        limit = request.args.get('limit', 50, type=int)
        status = request.args.get('status', None)
        scans = db.get_scheduled_scans(limit=limit, status=status)
        return jsonify({
            "success": True,
            "scans": scans
        })
    except Exception as e:
        logger.error(f"Error fetching scheduled scans: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/scheduled-scans', methods=['POST'])
def create_scheduled_scan():
    """Create a new scheduled scan"""
    try:
        data = request.json or {}
        directory = data.get("directory", db.get_setting("default_directory", ""))
        scheduled_for_raw = data.get("scheduled_for", "")

        if not directory:
            return jsonify({
                "success": False,
                "error": "No directory specified"
            }), 400

        scheduled_for = parse_iso_datetime(scheduled_for_raw)
        if not scheduled_for:
            return jsonify({
                "success": False,
                "error": "Invalid scheduled time"
            }), 400

        scan_id = db.create_scheduled_scan(directory, scheduled_for)
        return jsonify({
            "success": True,
            "id": scan_id
        })
    except Exception as e:
        logger.error(f"Error creating scheduled scan: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/scheduled-scans/<int:scan_id>/cancel', methods=['POST'])
def cancel_scheduled_scan(scan_id):
    """Cancel a scheduled scan"""
    try:
        success = db.cancel_scheduled_scan(scan_id)
        return jsonify({
            "success": success
        })
    except Exception as e:
        logger.error(f"Error cancelling scheduled scan: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/suggested-matches', methods=['POST'])
def save_suggested_matches():
    """Save suggested matches for files"""
    try:
        data = request.json
        matches = data.get("matches", {})

        for file_path, match_data in matches.items():
            file_name = Path(file_path).name
            db.save_suggested_match(file_path, file_name, match_data)

        return jsonify({
            "success": True,
            "count": len(matches)
        })

    except Exception as e:
        logger.error(f"Error saving suggested matches: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/folder-rules', methods=['GET'])
def get_folder_rules():
    """Get all folder rules"""
    try:
        rules = db.get_all_folder_rules()
        return jsonify({
            "success": True,
            "rules": rules
        })
    except Exception as e:
        logger.error(f"Error fetching folder rules: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/folder-rules', methods=['POST'])
def save_folder_rule():
    """Create or update a folder rule"""
    try:
        data = request.json or {}
        directory = data.get("directory", "").strip()
        if not directory:
            return jsonify({
                "success": False,
                "error": "Directory is required"
            }), 400

        success = db.upsert_folder_rule(directory, data)
        return jsonify({
            "success": success
        })
    except Exception as e:
        logger.error(f"Error saving folder rule: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/folder-rules/<path:directory>', methods=['DELETE'])
def delete_folder_rule(directory):
    """Delete a folder rule for a directory"""
    try:
        success = db.delete_folder_rule(directory)
        return jsonify({
            "success": success
        })
    except Exception as e:
        logger.error(f"Error deleting folder rule: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/suggested-matches/<path:file_path>', methods=['DELETE'])
def delete_suggested_match(file_path):
    """Delete a suggested match for a file"""
    try:
        success = db.delete_suggested_match(file_path)
        return jsonify({
            "success": success
        })
    except Exception as e:
        logger.error(f"Error deleting suggested match: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/suggested-matches', methods=['DELETE'])
def clear_all_suggested_matches():
    """Clear all suggested matches and reset scan state"""
    try:
        # Clear database suggested matches
        success = db.clear_all_suggested_matches()

        # CRITICAL: Reset in-memory scan state to guarantee clean slate
        global scan_state
        scan_state["files"] = []
        scan_state["scanning"] = False
        scan_state["last_scan"] = None

        logger.info("Cleared all suggested matches and reset scan state")

        return jsonify({
            "success": success
        })
    except Exception as e:
        logger.error(f"Error clearing suggested matches: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============ MAINTENANCE ENDPOINTS ============

@app.route('/api/maintenance/reset-settings', methods=['POST'])
def reset_settings():
    """Clear all settings, optionally keeping API keys"""
    try:
        data = request.json or {}
        keep_api_keys = bool(data.get("keep_api_keys", False))
        success = db.clear_settings(keep_api_keys=keep_api_keys)
        initialize_clients()
        return jsonify({
            "success": success
        })
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/maintenance/clear-history', methods=['POST'])
def clear_history():
    """Clear processing runs, scan history, scheduled scans, and API usage logs"""
    try:
        success = db.clear_history_and_logs()
        return jsonify({
            "success": success
        })
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/maintenance/clear-caches', methods=['POST'])
def clear_caches():
    """Clear cached data like suggested matches and reset scan state"""
    try:
        success = db.clear_all_suggested_matches()
        global scan_state
        scan_state["files"] = []
        scan_state["scanning"] = False
        scan_state["last_scan"] = None
        return jsonify({
            "success": success
        })
    except Exception as e:
        logger.error(f"Error clearing caches: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============ SEARCH ENDPOINTS ============

@app.route('/api/search', methods=['POST'])
def search_title():
    """Search for title matches from OMDb/TMDb

    Query params:
        query: The search query (required)
        mode: "quick" (default) for single best match (1 API call),
              "full" for multiple results to choose from (2 API calls)
    """
    try:
        data = request.json
        query = data.get("query", "").strip()
        mode = data.get("mode", "quick")  # "quick" or "full"

        if not query:
            return jsonify({
                "success": False,
                "error": "No search query provided"
            }), 400

        if not omdb_client and not tmdb_client:
            return jsonify({
                "success": False,
                "error": "API not configured"
            }), 400

        preferred_source = data.get("preferred_source") or _get_str_setting("preferred_source", "omdb")
        language = data.get("language")

        results = []
        if preferred_source == "tmdb" and tmdb_client:
            try:
                import aiohttp
                import asyncio

                async def tmdb_search(title, mode, language=None):
                    """TMDb search with optional language support (1 API call)"""
                    start_time = time.time()

                    url = f"{tmdb_client.base_url}/search/multi"
                    params = {
                        "api_key": tmdb_client.api_key,
                        "query": title
                    }
                    if language:
                        params["language"] = language

                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, params=params) as resp:
                            response_time_ms = int((time.time() - start_time) * 1000)
                            if resp.status != 200:
                                db.track_api_call(
                                    provider="tmdb",
                                    endpoint="/search/multi",
                                    success=False,
                                    response_time_ms=response_time_ms,
                                    call_count=1
                                )
                                return []

                            data = await resp.json()
                            items = [
                                item for item in data.get("results", [])
                                if item.get("media_type") in ("movie", "tv")
                            ]
                            if mode == "quick":
                                items = items[:1]
                            else:
                                items = items[:5]

                            results = []
                            for item in items:
                                title_value = item.get("title") or item.get("name")
                                date_value = item.get("release_date") or item.get("first_air_date") or ""
                                year = date_value[:4] if date_value else "N/A"
                                poster_path = item.get("poster_path")
                                poster = f"https://image.tmdb.org/t/p/w185{poster_path}" if poster_path else None
                                vote_average = item.get("vote_average")
                                imdb_rating = f"{vote_average:.1f}/10" if isinstance(vote_average, (int, float)) else "N/A"

                                results.append({
                                    "title": title_value,
                                    "year": year,
                                    "plot": item.get("overview") or "No plot available",
                                    "runtime": None,
                                    "imdb_rating": imdb_rating,
                                    "media_type": item.get("media_type"),
                                    "poster": poster,
                                    "imdb_id": None
                                })

                            db.track_api_call(
                                provider="tmdb",
                                endpoint="/search/multi",
                                success=True,
                                response_time_ms=response_time_ms,
                                call_count=1
                            )
                            return results

                results = asyncio.run(tmdb_search(query, mode, language))
                return jsonify({
                    "success": True,
                    "results": results
                })

            except Exception as e:
                logger.error(f"Error searching TMDb: {e}")

        if omdb_client:
            try:
                import aiohttp
                import asyncio

                async def omdb_quick_search(title):
                    """Quick search - single best match (1 API call)"""
                    start_time = time.time()

                    params = {
                        "apikey": omdb_client.api_key,
                        "t": title,
                        "type": "movie",
                        "plot": "short"
                    }

                    async with aiohttp.ClientSession() as session:
                        async with session.get(omdb_client.BASE_URL, params=params) as resp:
                            response_time_ms = int((time.time() - start_time) * 1000)

                            if resp.status == 200:
                                data = await resp.json()
                                if data.get("Response") == "True":
                                    db.track_api_call(
                                        provider="omdb",
                                        endpoint=f"/title?t={title}",
                                        success=True,
                                        response_time_ms=response_time_ms,
                                        call_count=1
                                    )
                                    return [{
                                        "title": data.get("Title"),
                                        "year": data.get("Year"),
                                        "plot": data.get("Plot", "No plot available"),
                                        "runtime": data.get("Runtime", "N/A"),
                                        "imdb_rating": data.get("imdbRating", "N/A"),
                                        "media_type": data.get("Type"),
                                        "poster": data.get("Poster"),
                                        "imdb_id": data.get("imdbID"),
                                        "director": data.get("Director", "N/A"),
                                        "actors": data.get("Actors", "N/A"),
                                        "released": data.get("Released", "N/A"),
                                        "genre": data.get("Genre", "N/A")
                                    }]

                            db.track_api_call(
                                provider="omdb",
                                endpoint=f"/title?t={title}",
                                success=False,
                                response_time_ms=response_time_ms,
                                call_count=1
                            )
                            return []

                async def omdb_full_search(title):
                    """Full search - multiple results with details (2 API calls)"""
                    start_time = time.time()
                    api_calls = 0

                    # First: search to get list of matches
                    search_params = {
                        "apikey": omdb_client.api_key,
                        "s": title,
                        "type": "movie"
                    }

                    async with aiohttp.ClientSession() as session:
                        async with session.get(omdb_client.BASE_URL, params=search_params) as resp:
                            api_calls += 1
                            if resp.status != 200:
                                return []

                            data = await resp.json()
                            if data.get("Response") != "True":
                                response_time_ms = int((time.time() - start_time) * 1000)
                                db.track_api_call(
                                    provider="omdb",
                                    endpoint=f"/search?s={title}",
                                    success=False,
                                    response_time_ms=response_time_ms,
                                    call_count=1
                                )
                                return []

                            search_results = data.get("Search", [])[:5]
                            if not search_results:
                                return []

                            # Second: get details for each result so manual selections have full metadata
                            detailed_results = []
                            for item in search_results:
                                detail_params = {
                                    "apikey": omdb_client.api_key,
                                    "i": item.get("imdbID"),
                                    "plot": "short"
                                }
                                async with session.get(omdb_client.BASE_URL, params=detail_params) as detail_resp:
                                    api_calls += 1
                                    if detail_resp.status == 200:
                                        detail_data = await detail_resp.json()
                                        if detail_data.get("Response") == "True":
                                            detailed_results.append({
                                                "title": detail_data.get("Title"),
                                                "year": detail_data.get("Year"),
                                                "plot": detail_data.get("Plot", "No plot available"),
                                                "runtime": detail_data.get("Runtime", "N/A"),
                                                "imdb_rating": detail_data.get("imdbRating", "N/A"),
                                                "media_type": detail_data.get("Type"),
                                                "poster": detail_data.get("Poster"),
                                                "imdb_id": detail_data.get("imdbID"),
                                                "director": detail_data.get("Director", "N/A"),
                                                "actors": detail_data.get("Actors", "N/A"),
                                                "released": detail_data.get("Released", "N/A"),
                                                "genre": detail_data.get("Genre", "N/A")
                                            })
                                            continue
                                # Fallback to basic info if detail lookup fails
                                detailed_results.append({
                                    "title": item.get("Title"),
                                    "year": item.get("Year"),
                                    "plot": None,
                                    "runtime": None,
                                    "imdb_rating": None,
                                    "media_type": item.get("Type"),
                                    "poster": item.get("Poster"),
                                    "imdb_id": item.get("imdbID"),
                                    "director": "N/A",
                                    "actors": "N/A",
                                    "released": "N/A",
                                    "genre": "N/A"
                                })

                            response_time_ms = int((time.time() - start_time) * 1000)
                            db.track_api_call(
                                provider="omdb",
                                endpoint=f"/search?s={title}",
                                success=True,
                                response_time_ms=response_time_ms,
                                call_count=api_calls
                            )

                            return detailed_results

                # Choose search mode
                if mode == "full":
                    results = asyncio.run(omdb_full_search(query))
                else:
                    results = asyncio.run(omdb_quick_search(query))

            except Exception as e:
                logger.error(f"Error searching OMDb: {e}")

        return jsonify({
            "success": True,
            "results": results
        })

    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============ PROCESSING ENDPOINTS ============

@app.route('/api/process', methods=['POST'])
def process_files():
    """Process selected files to add plot summaries"""
    try:
        data = request.json
        file_paths = data.get("files", [])
        duration = data.get("duration", db.get_setting("duration", 40))
        title_override = data.get("titleOverride", None)  # Optional title override
        force_reprocess = data.get("forceReprocess", False)  # Optional force flag

        if not file_paths:
            return jsonify({
                "success": False,
                "error": "No files specified"
            }), 400

        if not processor:
            return jsonify({
                "success": False,
                "error": "Metadata provider not configured"
            }), 400

        # Load default format options from settings
        format_options = get_format_options_from_settings()

        # Load strip_keywords setting (default True for better matching)
        strip_keywords = _get_bool_setting("strip_keywords", True)

        # Load clean_subtitle_content setting (default True for ad removal)
        clean_subtitle_content = _get_bool_setting("clean_subtitle_content", True)

        # Load default insertion position and preferred source
        default_insertion_position = _get_str_setting("insertion_position", "start")
        default_preferred_source = _get_str_setting("preferred_source", "omdb")

        folder_rules = db.get_all_folder_rules()

        # Create a processing run in database
        run_id = db.create_run(total_files=len(file_paths))

        results = []
        successful_count = 0
        failed_count = 0

        # Process each file
        for file_path in file_paths:
            try:
                # Process file asynchronously with optional title override
                rule = _get_folder_rule_for_path(file_path, folder_rules)
                effective_format = _merge_format_options(format_options, rule)
                insertion_position = rule.get("insertion_position") if rule else None
                preferred_source = rule.get("preferred_source") if rule else None
                language = rule.get("language") if rule else None

                result = asyncio.run(processor.process_file(
                    file_path,
                    duration,
                    force_reprocess=force_reprocess,
                    title_override=title_override,
                    format_options=effective_format,
                    strip_keywords=strip_keywords,
                    clean_subtitle_content=clean_subtitle_content,
                    insertion_position=insertion_position or default_insertion_position,
                    preferred_source=preferred_source or default_preferred_source,
                    language=language,
                ))

                # Track success/failure
                if result["success"]:
                    successful_count += 1
                else:
                    failed_count += 1

                # Save file result to database
                db.add_file_result(
                    run_id=run_id,
                    file_path=file_path,
                    success=result["success"],
                    status=result.get("status", "Unknown"),
                    summary=result.get("summary", "") if isinstance(result.get("summary"), str) else "",
                    error_message=result.get("error", ""),
                    duration=duration
                )

                results.append({
                    "file": file_path,
                    "success": result["success"],
                    "status": result.get("status", "Unknown"),
                    "summary": result.get("summary", ""),
                    "error": result.get("error")
                })

                # Update scan state
                for file_info in scan_state["files"]:
                    if file_info["path"] == file_path:
                        file_info["status"] = result.get("status", "Unknown")
                        file_info["summary"] = result.get("summary", "") if isinstance(result.get("summary"), str) else ""
                        file_info["has_plot"] = result["success"]
                        break

            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing {file_path}: {e}")

                # Save error result to database
                db.add_file_result(
                    run_id=run_id,
                    file_path=file_path,
                    success=False,
                    status="Error",
                    summary="",
                    error_message=str(e),
                    duration=duration
                )

                results.append({
                    "file": file_path,
                    "success": False,
                    "status": "Error",
                    "summary": "",
                    "error": str(e)
                })

        # Complete the run in database
        db.complete_run(run_id, successful_count, failed_count)

        return jsonify({
            "success": True,
            "results": results,
            "run_id": run_id
        })

    except Exception as e:
        logger.error(f"Processing error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/process/batch', methods=['POST'])
def process_batch():
    """Process multiple files with individual title overrides - streams progress via SSE

    Body: {
        items: [{ path: string, titleOverride: { title, year, plot, ... } }, ...],
        duration: number (optional)
    }

    Returns: SSE stream with progress updates and final results
    """
    try:
        data = request.json
        items = data.get("items", [])
        duration = data.get("duration", db.get_setting("duration", 40))

        if not items:
            return jsonify({
                "success": False,
                "error": "No items specified"
            }), 400

        if not processor:
            return jsonify({
                "success": False,
                "error": "Processor not initialized - check API key configuration"
            }), 400

        def generate():
            """Generator for SSE progress updates"""
            total = len(items)
            results = []
            successful_count = 0
            failed_count = 0

            # Load default format options from settings
            format_options = get_format_options_from_settings()

            # Load strip_keywords setting (default True for better matching)
            strip_keywords = _get_bool_setting("strip_keywords", True)

            # Load clean_subtitle_content setting (default True for ad removal)
            clean_subtitle_content = _get_bool_setting("clean_subtitle_content", True)

            default_insertion_position = _get_str_setting("insertion_position", "start")
            default_preferred_source = _get_str_setting("preferred_source", "omdb")
            folder_rules = db.get_all_folder_rules()

            # Create a processing run
            run_id = db.create_run(total_files=total)

            # Send initial status
            yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"

            for idx, item in enumerate(items):
                file_path = item.get("path")
                title_override = item.get("titleOverride")

                # Send progress update
                yield f"data: {json.dumps({'type': 'progress', 'current': idx + 1, 'total': total, 'file': Path(file_path).name if file_path else 'Unknown'})}\n\n"

                try:
                    # Process file with title override (no API call needed - data is pre-fetched)
                    rule = _get_folder_rule_for_path(file_path, folder_rules)
                    effective_format = _merge_format_options(format_options, rule)
                    insertion_position = rule.get("insertion_position") if rule else None
                    preferred_source = rule.get("preferred_source") if rule else None
                    language = rule.get("language") if rule else None

                    result = asyncio.run(processor.process_file(
                        file_path,
                        duration,
                        force_reprocess=True,  # Always reprocess when applying matches
                        title_override=title_override,
                        format_options=effective_format,
                        strip_keywords=strip_keywords,
                        clean_subtitle_content=clean_subtitle_content,
                        insertion_position=insertion_position or default_insertion_position,
                        preferred_source=preferred_source or default_preferred_source,
                        language=language,
                    ))

                    if result["success"]:
                        successful_count += 1
                    else:
                        failed_count += 1

                    # Save file result to database
                    db.add_file_result(
                        run_id=run_id,
                        file_path=file_path,
                        success=result["success"],
                        status=result.get("status", "Unknown"),
                        summary=result.get("summary", "") if isinstance(result.get("summary"), str) else "",
                        error_message=result.get("error", ""),
                        duration=duration
                    )

                    results.append({
                        "file": file_path,
                        "name": Path(file_path).name,
                        "success": result["success"],
                        "status": result.get("status", "Unknown"),
                        "error": result.get("error")
                    })

                    # Send individual result
                    yield f"data: {json.dumps({'type': 'result', 'file': Path(file_path).name, 'success': result['success'], 'status': result.get('status', 'Unknown')})}\n\n"

                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error processing {file_path}: {e}")

                    db.add_file_result(
                        run_id=run_id,
                        file_path=file_path,
                        success=False,
                        status="Error",
                        summary="",
                        error_message=str(e),
                        duration=duration
                    )

                    results.append({
                        "file": file_path,
                        "name": Path(file_path).name if file_path else "Unknown",
                        "success": False,
                        "status": "Error",
                        "error": str(e)
                    })

                    yield f"data: {json.dumps({'type': 'result', 'file': Path(file_path).name if file_path else 'Unknown', 'success': False, 'status': 'Error', 'error': str(e)})}\n\n"

            # Complete the run
            db.complete_run(run_id, successful_count, failed_count)

            # Send completion
            yield f"data: {json.dumps({'type': 'complete', 'success': True, 'total': total, 'successful': successful_count, 'failed': failed_count, 'run_id': run_id})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive'
            }
        )

    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============ HEALTH ENDPOINT ============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    omdb_enabled = bool(db.get_setting("omdb_enabled", False))
    tmdb_enabled = bool(db.get_setting("tmdb_enabled", False))
    tvmaze_enabled = bool(db.get_setting("tvmaze_enabled", False))
    omdb_configured = bool(db.get_setting("omdb_api_key") or db.get_setting("api_key"))
    tmdb_configured = bool(db.get_setting("tmdb_api_key"))

    return jsonify({
        "status": "ok",
        "api_key_configured": (omdb_enabled and omdb_configured) or (tmdb_enabled and tmdb_configured) or tvmaze_enabled,
        "omdb_configured": omdb_configured,
        "tmdb_configured": tmdb_configured,
        "omdb_enabled": omdb_enabled,
        "tmdb_enabled": tmdb_enabled,
        "tvmaze_enabled": tvmaze_enabled
    })


# ============ HISTORY ENDPOINTS ============

@app.route('/api/history/runs', methods=['GET'])
def get_run_history():
    """Get processing run history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = db.get_run_history(limit=limit)
        return jsonify({
            "success": True,
            "runs": history
        })
    except Exception as e:
        logger.error(f"Error fetching run history: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/history/runs/<int:run_id>', methods=['GET'])
def get_run_details_endpoint(run_id):
    """Get detailed information about a specific run"""
    try:
        details = db.get_run_details(run_id)
        if details:
            return jsonify({
                "success": True,
                "run": details
            })
        else:
            return jsonify({
                "success": False,
                "error": "Run not found"
            }), 404
    except Exception as e:
        logger.error(f"Error fetching run details: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/history/scans', methods=['GET'])
def get_scan_history():
    """Get scan history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = db.get_scan_history(limit=limit)
        return jsonify({
            "success": True,
            "scans": history
        })
    except Exception as e:
        logger.error(f"Error fetching scan history: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/library', methods=['GET'])
def get_library_report():
    """Get library health report with scan files and issue summaries"""
    try:
        page_size = request.args.get('page_size', type=int)
        page = request.args.get('page', type=int)
        if page_size is None:
            page_size = request.args.get('limit', 200, type=int)
        if page is None:
            offset = request.args.get('offset', 0, type=int)
            page = (offset // page_size) + 1 if page_size else 1

        latest_files = db.get_latest_scan_files(limit=None, offset=0)
        latest_results = db.get_latest_file_results()
        items = _build_library_items(latest_files, latest_results, None)

        total_items = len(items)
        start = max(0, (page - 1) * page_size)
        end = start + page_size
        page_items = items[start:end]

        return jsonify({
            "success": True,
            "items": page_items,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "has_more": end < total_items
        })
    except Exception as e:
        logger.error(f"Error fetching library report: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get overall statistics"""
    try:
        stats = db.get_statistics()
        return jsonify({
            "success": True,
            "statistics": stats
        })
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============ API USAGE ENDPOINTS ============

@app.route('/api/integrations/usage', methods=['GET'])
def get_integration_usage():
    """Get API usage statistics for all integrations"""
    try:
        usage_stats = db.get_all_usage_stats()
        return jsonify({
            "success": True,
            "usage": usage_stats
        })
    except Exception as e:
        logger.error(f"Error fetching integration usage: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============ ROOT ENDPOINT ============

@app.route('/')
def index():
    """Serve the frontend application or API info"""
    # Check if static files exist (production mode)
    index_path = os.path.join(static_folder, 'index.html')
    if os.path.exists(index_path):
        return app.send_static_file('index.html')

    # Development mode - return API info
    return jsonify({
        "name": "Sublogue API",
        "version": "1.0.0",
        "endpoints": {
            "GET /api/health": "Health check",
            "GET /api/settings": "Get settings",
            "POST /api/settings": "Update settings",
            "POST /api/scan/start": "Start directory scan",
            "GET /api/scan/status": "Get scan status",
            "POST /api/process": "Process files",
            "GET /api/history/runs": "Get processing run history",
            "GET /api/history/runs/<id>": "Get run details",
            "GET /api/history/scans": "Get scan history",
            "GET /api/statistics": "Get overall statistics",
            "GET /api/integrations/usage": "Get API usage statistics"
        }
    })


@app.errorhandler(404)
def not_found(e):
    """Handle 404 - serve index.html for SPA routing"""
    index_path = os.path.join(static_folder, 'index.html')
    if os.path.exists(index_path):
        return app.send_static_file('index.html')
    return jsonify({"error": "Not found"}), 404


if __name__ == '__main__':
    logger.info("Starting Sublogue API server on http://localhost:5000")
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        start_scheduled_scan_worker()
    app.run(debug=True, host='0.0.0.0', port=5000)
