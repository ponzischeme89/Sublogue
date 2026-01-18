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
    """Scheduler for automation rules."""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self._scheduler = BackgroundScheduler(daemon=True)
        self._lock = threading.Lock()
        self._started = False

    def start(self):
        with self._lock:
            if self._started:
                return
            self._scheduler.start()
            self._started = True
            self.reload_rules()
            logger.info("Automation scheduler started")

    def shutdown(self):
        with self._lock:
            if not self._started:
                return
            self._scheduler.shutdown(wait=False)
            self._started = False
            logger.info("Automation scheduler stopped")

    def reload_rules(self):
        """Reload all automation rules from storage."""
        with self._lock:
            self._scheduler.remove_all_jobs()
            rules = self._load_rules()
            for rule in rules:
                if not rule.enabled:
                    continue
                self._schedule_rule(rule)

    def run_rule_now(self, rule_id: str, dry_run: bool = False) -> dict:
        rule = self._get_rule(rule_id)
        if not rule:
            return {"success": False, "error": "Rule not found"}
        return self._execute_rule(rule, dry_run=dry_run)

    def _load_rules(self) -> List[AutomationRule]:
        rules_raw = self.db_manager.get_automation_rules()
        return [AutomationRule.from_dict(r) for r in rules_raw]

    def _get_rule(self, rule_id: str) -> Optional[AutomationRule]:
        raw = self.db_manager.get_automation_rule(rule_id)
        return AutomationRule.from_dict(raw) if raw else None

    def _schedule_rule(self, rule: AutomationRule):
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

    def _run_rule_job(self, rule_id: str):
        rule = self._get_rule(rule_id)
        if not rule or not rule.enabled:
            return
        self._execute_rule(rule, dry_run=False)

    def _execute_rule(self, rule: AutomationRule, dry_run: bool) -> dict:
        files = enumerate_srt_files(rule.target_folders)
        modified = 0
        total_removed = 0
        errors: List[str] = []

        for file_path in files:
            try:
                did_modify, removed_lines = remove_lines_matching_patterns(
                    str(file_path),
                    rule.patterns,
                    dry_run=dry_run,
                )
                if did_modify:
                    modified += 1
                    total_removed += removed_lines
                self.db_manager.add_automation_log(
                    rule_id=rule.id,
                    file_path=str(file_path),
                    modified=did_modify,
                    removed_lines=removed_lines,
                    dry_run=dry_run,
                    error_message=None,
                )
            except Exception as e:
                errors.append(f"{file_path}: {e}")
                self.db_manager.add_automation_log(
                    rule_id=rule.id,
                    file_path=str(file_path),
                    modified=False,
                    removed_lines=0,
                    dry_run=dry_run,
                    error_message=str(e),
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
