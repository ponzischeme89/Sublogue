from __future__ import annotations

import threading
from typing import Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from logging_utils import get_logger
from automations.actions import enumerate_srt_files, remove_lines_matching_patterns
from automations.models import AutomationRule

logger = get_logger(__name__)


class AutomationEngine:
    """Scheduler for automation rules with aggressive diagnostic logging."""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self._scheduler = BackgroundScheduler(daemon=True)
        self._lock = threading.Lock()
        self._started = False
        logger.debug("AutomationEngine initialized with db_manager=%s", type(db_manager).__name__)

    # ------------------------------------------------------------------
    # START / STOP
    # ------------------------------------------------------------------
    def start(self):
        with self._lock:
            if self._started:
                logger.warning("Automation scheduler start() called, but it's already started.")
                return

            logger.info("Starting automation scheduler...")
            self._scheduler.start()
            self._started = True
            self.reload_rules()
            logger.info("Automation scheduler successfully started.")

    def shutdown(self):
        with self._lock:
            if not self._started:
                logger.warning("shutdown() called but scheduler was not started.")
                return

            logger.info("Shutting down automation scheduler...")
            self._scheduler.shutdown(wait=False)
            self._started = False
            logger.info("Automation scheduler fully stopped.")

    # ------------------------------------------------------------------
    # RULE MANAGEMENT
    # ------------------------------------------------------------------
    def reload_rules(self):
        """Reload all automation rules from storage."""
        logger.info("Reloading automation rules from database...")

        with self._lock:
            self._scheduler.remove_all_jobs()
            logger.debug("Cleared all scheduled jobs.")

            rules = self._load_rules()
            logger.info("Loaded %d automation rules.", len(rules))

            for rule in rules:
                logger.debug("Evaluating rule %s (enabled=%s, schedule=%s)", rule.id, rule.enabled, rule.schedule)

                if not rule.enabled:
                    logger.info("Rule %s is disabled — skipping scheduling.", rule.id)
                    continue

                self._schedule_rule(rule)

    def run_rule_now(self, rule_id: str, dry_run: bool = False) -> dict:
        logger.info("Manual execution requested for rule %s (dry_run=%s)", rule_id, dry_run)

        rule = self._get_rule(rule_id)
        if not rule:
            logger.error("Cannot execute — rule %s not found.", rule_id)
            return {"success": False, "error": "Rule not found"}

        return self._execute_rule(rule, dry_run=dry_run)

    def _load_rules(self) -> List[AutomationRule]:
        logger.debug("Fetching automation rules from database...")
        rules_raw = self.db_manager.get_automation_rules()
        rules = [AutomationRule.from_dict(r) for r in rules_raw]
        logger.debug("Database returned %d rules.", len(rules))
        return rules

    def _get_rule(self, rule_id: str) -> Optional[AutomationRule]:
        logger.debug("Fetching rule %s from database...", rule_id)
        raw = self.db_manager.get_automation_rule(rule_id)
        if raw:
            logger.debug("Rule %s found.", rule_id)
        else:
            logger.warning("Rule %s not found.", rule_id)
        return AutomationRule.from_dict(raw) if raw else None

    # ------------------------------------------------------------------
    # SCHEDULING
    # ------------------------------------------------------------------
    def _schedule_rule(self, rule: AutomationRule):
        logger.info("Scheduling rule %s with cron: %s", rule.id, rule.schedule)

        try:
            trigger = CronTrigger.from_crontab(rule.schedule)
        except ValueError as e:
            logger.error("Invalid cron schedule for rule %s: %s", rule.id, e)
            return

        self._scheduler.add_job(
            self._run_rule_job,
            trigger=trigger,
            args=[rule.id],
            id=f"automation:{rule.id}",
            replace_existing=True,
            misfire_grace_time=300,
            max_instances=1,
        )

        logger.info("Rule %s scheduled successfully.", rule.id)

    # ------------------------------------------------------------------
    # JOB EXECUTION
    # ------------------------------------------------------------------
    def _run_rule_job(self, rule_id: str):
        logger.info("Executing scheduled job for rule %s...", rule_id)
        rule = self._get_rule(rule_id)

        if not rule:
            logger.error("Scheduled rule %s no longer exists in database.", rule_id)
            return

        if not rule.enabled:
            logger.info("Scheduled rule %s is now disabled — skipping execution.", rule_id)
            return

        self._execute_rule(rule, dry_run=False)

    # ------------------------------------------------------------------
    # CORE EXECUTION LOGIC
    # ------------------------------------------------------------------
    def _execute_rule(self, rule: AutomationRule, dry_run: bool) -> dict:
        logger.info(
            "Executing rule %s (dry_run=%s). Target folders: %s | Patterns: %s",
            rule.id, dry_run, rule.target_folders, rule.patterns
        )

        files = enumerate_srt_files(rule.target_folders)
        logger.info("Rule %s scanning %d SRT files...", rule.id, len(files))

        modified = 0
        total_removed = 0
        errors: List[str] = []

        for file_path in files:
            logger.debug("Processing file: %s", file_path)

            try:
                did_modify, removed_lines = remove_lines_matching_patterns(
                    str(file_path),
                    rule.patterns,
                    dry_run=dry_run,
                )

                logger.debug(
                    "File processed: modified=%s, removed_lines=%d, path=%s",
                    did_modify, removed_lines, file_path
                )

                if did_modify:
                    modified += 1
                    total_removed += removed_lines

                # log into DB
                self.db_manager.add_automation_log(
                    rule_id=rule.id,
                    file_path=str(file_path),
                    modified=did_modify,
                    removed_lines=removed_lines,
                    dry_run=dry_run,
                    error_message=None,
                )

            except Exception as e:
                logger.exception("Error while processing file %s under rule %s", file_path, rule.id)
                errors.append(f"{file_path}: {e}")

                self.db_manager.add_automation_log(
                    rule_id=rule.id,
                    file_path=str(file_path),
                    modified=False,
                    removed_lines=0,
                    dry_run=dry_run,
                    error_message=str(e),
                )

        logger.info(
            "Finished executing rule %s. Files scanned=%d | Modified=%d | Removed lines=%d | Errors=%d",
            rule.id, len(files), modified, total_removed, len(errors)
        )

        return {
            "success": True,
            "rule_id": rule.id,
            "files_scanned": len(files),
            "files_modified": modified,
            "removed_lines": total_removed,
            "dry_run": dry_run,
            "errors": errors,
        }
