"""
Configuration manager - handles settings persistence
"""
import json
import logging
from logging_utils import get_logger
from pathlib import Path

logger = get_logger(__name__)


class ConfigManager:
    """Manages application settings with JSON persistence"""

    def __init__(self, file_path="settings.json"):
        self.file_path = Path(file_path)
        self.settings = {
            "api_key": "",
            "default_directory": "",
            "duration": 40,
            "cleaning_patterns": [
                r"\(\d{4}\)",
                r"\[\d{4}\]",
                r"\.\d{4}\.",
                r"\.(19|20)\d{2}",
                r"\.[a-z]{2,3}\b",
                r"\.(?:720p|1080p|2160p|480p|HDRip|BRRip|BluRay|WEBRip|WEB-DL)",
                r"\.(?:x264|x265|HEVC|AAC|AC3|DTS)"
            ]
        }
        self.load_settings()

    def load_settings(self):
        """Load settings from disk"""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r") as f:
                    self.settings.update(json.load(f))
                logger.info("Settings loaded successfully")
            except Exception as e:
                logger.error(f"Error loading settings: {e}")

    def save_settings(self):
        """Save settings to disk"""
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.settings, f, indent=2)
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Set a setting value"""
        self.settings[key] = value
        logger.info(f"Setting updated: {key}")

    def get_all(self):
        """Get all settings"""
        return self.settings.copy()

    def update_multiple(self, updates):
        """Update multiple settings at once"""
        self.settings.update(updates)
        logger.info(f"Updated {len(updates)} settings")
