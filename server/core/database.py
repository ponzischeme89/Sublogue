"""
Database layer using SQLAlchemy with SQLite
Handles persistent storage for settings, runs, and history
"""
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
import json
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class Settings(Base):
    """Settings table - stores application configuration"""
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Settings(key='{self.key}', value='{self.value}')>"


class ProcessingRun(Base):
    """Processing runs table - stores each batch processing session"""
    __tablename__ = 'processing_runs'

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime)
    total_files = Column(Integer, default=0)
    successful_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    duration_seconds = Column(Float)
    status = Column(String(50), default='in_progress')  # in_progress, completed, failed

    # Relationship to file results
    file_results = relationship("FileResult", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProcessingRun(id={self.id}, started_at='{self.started_at}', status='{self.status}')>"


class FileResult(Base):
    """File results table - stores individual file processing results"""
    __tablename__ = 'file_results'

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('processing_runs.id'), nullable=False, index=True)
    file_path = Column(String(500), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    success = Column(Boolean, default=False)
    status = Column(String(100))
    summary = Column(Text)
    error_message = Column(Text)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    duration = Column(Integer)  # subtitle duration in seconds

    # Relationship back to run
    run = relationship("ProcessingRun", back_populates="file_results")

    def __repr__(self):
        return f"<FileResult(id={self.id}, file_name='{self.file_name}', success={self.success})>"


class ScanHistory(Base):
    """Scan history table - stores directory scan history"""
    __tablename__ = 'scan_history'

    id = Column(Integer, primary_key=True)
    directory = Column(String(500), nullable=False, index=True)
    scanned_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    files_found = Column(Integer, default=0)
    files_with_plot = Column(Integer, default=0)
    scan_duration_ms = Column(Integer)

    def __repr__(self):
        return f"<ScanHistory(id={self.id}, directory='{self.directory}', files_found={self.files_found})>"


class ScheduledScan(Base):
    """Scheduled scans table - stores scheduled scan jobs and results"""
    __tablename__ = 'scheduled_scans'

    id = Column(Integer, primary_key=True)
    directory = Column(String(500), nullable=False, index=True)
    scheduled_for = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    status = Column(String(50), default='scheduled', index=True)  # scheduled, running, completed, cancelled, failed
    files_found = Column(Integer, default=0)
    files_with_plot = Column(Integer, default=0)
    scan_duration_ms = Column(Integer)
    error_message = Column(Text)

    def __repr__(self):
        return f"<ScheduledScan(id={self.id}, directory='{self.directory}', status='{self.status}')>"


class ApiUsage(Base):
    """API usage tracking table - monitors API calls per integration"""
    __tablename__ = 'api_usage'

    id = Column(Integer, primary_key=True)
    provider = Column(String(50), nullable=False, index=True)  # omdb, tmdb, tvmaze
    endpoint = Column(String(200))  # Specific endpoint called
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    success = Column(Boolean, default=True)
    response_time_ms = Column(Integer)
    call_count = Column(Integer, default=1)  # Number of API calls in this batch

    def __repr__(self):
        return f"<ApiUsage(id={self.id}, provider='{self.provider}', calls={self.call_count}, timestamp='{self.timestamp}')>"


class SuggestedMatch(Base):
    """Suggested matches table - stores auto-matched titles for files"""
    __tablename__ = 'suggested_matches'

    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), nullable=False, unique=True, index=True)
    file_name = Column(String(255), nullable=False)
    matched_title = Column(String(255), nullable=False)
    matched_year = Column(String(10))
    matched_imdb_id = Column(String(50))
    match_data = Column(Text)  # JSON blob with full match data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SuggestedMatch(id={self.id}, file_name='{self.file_name}', matched_title='{self.matched_title}')>"


class FolderRule(Base):
    """Folder-specific rules that override default settings"""
    __tablename__ = 'folder_rules'

    id = Column(Integer, primary_key=True)
    directory = Column(String(500), nullable=False, unique=True, index=True)
    preferred_source = Column(String(50))
    insertion_position = Column(String(50))
    language = Column(String(20))
    subtitle_title_bold = Column(Boolean)
    subtitle_plot_italic = Column(Boolean)
    subtitle_show_director = Column(Boolean)
    subtitle_show_actors = Column(Boolean)
    subtitle_show_released = Column(Boolean)
    subtitle_show_genre = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<FolderRule(id={self.id}, directory='{self.directory}')>"


class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self, db_path="sublogue.db"):
        """Initialize database connection"""
        self.db_path = Path(db_path)
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        self.Session = scoped_session(sessionmaker(bind=self.engine))

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        logger.info(f"Database initialized at {self.db_path}")

    def get_session(self):
        """Get a new database session"""
        return self.Session()

    def close_session(self):
        """Close the session"""
        self.Session.remove()

    # ============ SETTINGS OPERATIONS ============

    def get_setting(self, key, default=None):
        """Get a setting value"""
        session = self.get_session()
        try:
            setting = session.query(Settings).filter_by(key=key).first()
            if setting:
                try:
                    return json.loads(setting.value)
                except json.JSONDecodeError:
                    return setting.value
            return default
        finally:
            session.close()

    def set_setting(self, key, value):
        """Set a setting value"""
        session = self.get_session()
        try:
            setting = session.query(Settings).filter_by(key=key).first()

            # Convert value to JSON string
            json_value = json.dumps(value) if not isinstance(value, str) else value

            if setting:
                setting.value = json_value
                setting.updated_at = datetime.utcnow()
            else:
                setting = Settings(key=key, value=json_value)
                session.add(setting)

            session.commit()
            logger.info(f"Setting updated: {key}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error setting value: {e}")
            raise
        finally:
            session.close()

    def get_all_settings(self):
        """Get all settings as a dictionary"""
        session = self.get_session()
        try:
            settings = session.query(Settings).all()
            result = {}
            for setting in settings:
                try:
                    result[setting.key] = json.loads(setting.value)
                except json.JSONDecodeError:
                    result[setting.key] = setting.value
            return result
        finally:
            session.close()

    def update_settings(self, settings_dict):
        """Update multiple settings at once"""
        for key, value in settings_dict.items():
            self.set_setting(key, value)

    # ============ PROCESSING RUN OPERATIONS ============

    def create_run(self, total_files):
        """Create a new processing run"""
        session = self.get_session()
        try:
            run = ProcessingRun(
                total_files=total_files,
                status='in_progress'
            )
            session.add(run)
            session.commit()
            run_id = run.id
            logger.info(f"Created processing run {run_id}")
            return run_id
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating run: {e}")
            raise
        finally:
            session.close()

    def complete_run(self, run_id, successful_files, failed_files):
        """Mark a run as completed"""
        session = self.get_session()
        try:
            run = session.query(ProcessingRun).get(run_id)
            if run:
                run.completed_at = datetime.utcnow()
                run.successful_files = successful_files
                run.failed_files = failed_files
                run.status = 'completed'

                if run.started_at:
                    duration = (run.completed_at - run.started_at).total_seconds()
                    run.duration_seconds = duration

                session.commit()
                logger.info(f"Completed run {run_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error completing run: {e}")
            raise
        finally:
            session.close()

    def add_file_result(self, run_id, file_path, success, status, summary="", error_message="", duration=40):
        """Add a file processing result"""
        session = self.get_session()
        try:
            result = FileResult(
                run_id=run_id,
                file_path=file_path,
                file_name=Path(file_path).name,
                success=success,
                status=status,
                summary=summary,
                error_message=error_message,
                duration=duration
            )
            session.add(result)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding file result: {e}")
            raise
        finally:
            session.close()

    def get_run_history(self, limit=50):
        """Get processing run history"""
        session = self.get_session()
        try:
            runs = session.query(ProcessingRun).order_by(
                ProcessingRun.started_at.desc()
            ).limit(limit).all()

            result = []
            for run in runs:
                result.append({
                    'id': run.id,
                    'started_at': run.started_at.isoformat() if run.started_at else None,
                    'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                    'total_files': run.total_files,
                    'successful_files': run.successful_files,
                    'failed_files': run.failed_files,
                    'duration_seconds': run.duration_seconds,
                    'status': run.status
                })
            return result
        finally:
            session.close()

    def get_run_details(self, run_id):
        """Get detailed information about a specific run"""
        session = self.get_session()
        try:
            run = session.query(ProcessingRun).get(run_id)
            if not run:
                return None

            file_results = []
            for result in run.file_results:
                file_results.append({
                    'id': result.id,
                    'file_path': result.file_path,
                    'file_name': result.file_name,
                    'success': result.success,
                    'status': result.status,
                    'summary': result.summary,
                    'error_message': result.error_message,
                    'processed_at': result.processed_at.isoformat() if result.processed_at else None,
                    'duration': result.duration
                })

            return {
                'id': run.id,
                'started_at': run.started_at.isoformat() if run.started_at else None,
                'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                'total_files': run.total_files,
                'successful_files': run.successful_files,
                'failed_files': run.failed_files,
                'duration_seconds': run.duration_seconds,
                'status': run.status,
                'file_results': file_results
            }
        finally:
            session.close()

    # ============ SCAN HISTORY OPERATIONS ============

    def add_scan_history(self, directory, files_found, files_with_plot, scan_duration_ms):
        """Add a scan history entry"""
        session = self.get_session()
        try:
            scan = ScanHistory(
                directory=directory,
                files_found=files_found,
                files_with_plot=files_with_plot,
                scan_duration_ms=scan_duration_ms
            )
            session.add(scan)
            session.commit()
            logger.info(f"Scan history saved for {directory}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving scan history: {e}")
            raise
        finally:
            session.close()

    def get_scan_history(self, limit=50):
        """Get scan history"""
        session = self.get_session()
        try:
            scans = session.query(ScanHistory).order_by(
                ScanHistory.scanned_at.desc()
            ).limit(limit).all()

            result = []
            for scan in scans:
                result.append({
                    'id': scan.id,
                    'directory': scan.directory,
                    'scanned_at': scan.scanned_at.isoformat() if scan.scanned_at else None,
                    'files_found': scan.files_found,
                    'files_with_plot': scan.files_with_plot,
                    'scan_duration_ms': scan.scan_duration_ms
                })
            return result
        finally:
            session.close()

    # ============ SCHEDULED SCAN OPERATIONS ============

    def create_scheduled_scan(self, directory, scheduled_for):
        """Create a scheduled scan entry"""
        session = self.get_session()
        try:
            scheduled = ScheduledScan(
                directory=directory,
                scheduled_for=scheduled_for,
                status='scheduled'
            )
            session.add(scheduled)
            session.commit()
            return scheduled.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating scheduled scan: {e}")
            raise
        finally:
            session.close()

    def get_scheduled_scans(self, limit=50, status=None):
        """Get scheduled scans"""
        session = self.get_session()
        try:
            query = session.query(ScheduledScan)
            if status:
                query = query.filter_by(status=status)
            scans = query.order_by(ScheduledScan.scheduled_for.desc()).limit(limit).all()

            result = []
            for scan in scans:
                result.append({
                    'id': scan.id,
                    'directory': scan.directory,
                    'scheduled_for': scan.scheduled_for.isoformat() if scan.scheduled_for else None,
                    'created_at': scan.created_at.isoformat() if scan.created_at else None,
                    'started_at': scan.started_at.isoformat() if scan.started_at else None,
                    'completed_at': scan.completed_at.isoformat() if scan.completed_at else None,
                    'status': scan.status,
                    'files_found': scan.files_found,
                    'files_with_plot': scan.files_with_plot,
                    'scan_duration_ms': scan.scan_duration_ms,
                    'error_message': scan.error_message
                })
            return result
        finally:
            session.close()

    def get_scheduled_scan(self, scan_id):
        """Get a single scheduled scan by id"""
        session = self.get_session()
        try:
            scan = session.query(ScheduledScan).get(scan_id)
            if not scan:
                return None
            return {
                'id': scan.id,
                'directory': scan.directory,
                'scheduled_for': scan.scheduled_for.isoformat() if scan.scheduled_for else None,
                'created_at': scan.created_at.isoformat() if scan.created_at else None,
                'started_at': scan.started_at.isoformat() if scan.started_at else None,
                'completed_at': scan.completed_at.isoformat() if scan.completed_at else None,
                'status': scan.status,
                'files_found': scan.files_found,
                'files_with_plot': scan.files_with_plot,
                'scan_duration_ms': scan.scan_duration_ms,
                'error_message': scan.error_message
            }
        finally:
            session.close()

    def get_due_scheduled_scans(self, now):
        """Get scheduled scans that are due to run"""
        session = self.get_session()
        try:
            scans = session.query(ScheduledScan).filter(
                ScheduledScan.status == 'scheduled',
                ScheduledScan.scheduled_for <= now
            ).order_by(ScheduledScan.scheduled_for.asc()).all()
            return [scan.id for scan in scans]
        finally:
            session.close()

    def mark_scheduled_scan_running(self, scan_id, started_at=None):
        """Mark a scheduled scan as running"""
        session = self.get_session()
        try:
            scan = session.query(ScheduledScan).get(scan_id)
            if not scan or scan.status != 'scheduled':
                return False
            scan.status = 'running'
            scan.started_at = started_at or datetime.utcnow()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error marking scheduled scan running: {e}")
            return False
        finally:
            session.close()

    def complete_scheduled_scan(self, scan_id, files_found, files_with_plot, scan_duration_ms, completed_at=None):
        """Mark a scheduled scan as completed"""
        session = self.get_session()
        try:
            scan = session.query(ScheduledScan).get(scan_id)
            if not scan:
                return False
            scan.status = 'completed'
            scan.completed_at = completed_at or datetime.utcnow()
            scan.files_found = files_found
            scan.files_with_plot = files_with_plot
            scan.scan_duration_ms = scan_duration_ms
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error completing scheduled scan: {e}")
            return False
        finally:
            session.close()

    def fail_scheduled_scan(self, scan_id, error_message, completed_at=None):
        """Mark a scheduled scan as failed"""
        session = self.get_session()
        try:
            scan = session.query(ScheduledScan).get(scan_id)
            if not scan:
                return False
            scan.status = 'failed'
            scan.completed_at = completed_at or datetime.utcnow()
            scan.error_message = error_message
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error failing scheduled scan: {e}")
            return False
        finally:
            session.close()

    def cancel_scheduled_scan(self, scan_id):
        """Cancel a scheduled scan"""
        session = self.get_session()
        try:
            scan = session.query(ScheduledScan).get(scan_id)
            if not scan or scan.status != 'scheduled':
                return False
            scan.status = 'cancelled'
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error cancelling scheduled scan: {e}")
            return False
        finally:
            session.close()

    # ============ API USAGE OPERATIONS ============

    def track_api_call(self, provider, endpoint=None, success=True, response_time_ms=None, call_count=1):
        """Track API call(s) for usage monitoring

        Args:
            provider: API provider name (omdb, tmdb, tvmaze)
            endpoint: Specific endpoint called
            success: Whether the call(s) succeeded
            response_time_ms: Total response time in milliseconds
            call_count: Number of API calls made (for batched operations)
        """
        session = self.get_session()
        try:
            usage = ApiUsage(
                provider=provider,
                endpoint=endpoint,
                success=success,
                response_time_ms=response_time_ms,
                call_count=call_count
            )
            session.add(usage)
            session.commit()
            logger.debug(f"Tracked {call_count} API call(s) to {provider}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error tracking API call: {e}")
        finally:
            session.close()

    def get_api_usage_24h(self, provider):
        """Get API call count for the last 24 hours (sums call_count field)"""
        session = self.get_session()
        try:
            from datetime import timedelta
            from sqlalchemy import func

            cutoff_time = datetime.utcnow() - timedelta(hours=24)

            # Sum the call_count column to get total API calls
            result = session.query(func.coalesce(func.sum(ApiUsage.call_count), 0)).filter(
                ApiUsage.provider == provider,
                ApiUsage.timestamp >= cutoff_time
            ).scalar()

            return result or 0
        finally:
            session.close()

    def check_api_limit(self, provider, limit=1000):
        """Check if API usage is under the limit"""
        current_usage = self.get_api_usage_24h(provider)
        return {
            'under_limit': current_usage < limit,
            'current_usage': current_usage,
            'limit': limit,
            'remaining': max(0, limit - current_usage)
        }

    def get_usage_stats(self, provider):
        """Get detailed usage statistics for a provider"""
        session = self.get_session()
        try:
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=24)

            # Get 24h usage records
            usage_24h = session.query(ApiUsage).filter(
                ApiUsage.provider == provider,
                ApiUsage.timestamp >= cutoff_time
            ).all()

            # Sum call_count for accurate totals
            total_calls = sum(u.call_count or 1 for u in usage_24h)
            successful_calls = sum(u.call_count or 1 for u in usage_24h if u.success)
            failed_calls = total_calls - successful_calls

            # Calculate average response time (weighted by call count)
            weighted_times = [(u.response_time_ms or 0) * (u.call_count or 1) for u in usage_24h if u.response_time_ms is not None]
            avg_response_time = sum(weighted_times) / total_calls if total_calls > 0 and weighted_times else 0

            # Find oldest call in 24h window to calculate reset time
            oldest_call = min([u.timestamp for u in usage_24h]) if usage_24h else datetime.utcnow()
            reset_time = oldest_call + timedelta(hours=24)

            return {
                'provider': provider,
                'total_calls_24h': total_calls,
                'successful_calls': successful_calls,
                'failed_calls': failed_calls,
                'avg_response_time_ms': round(avg_response_time, 2),
                'reset_time': reset_time.isoformat(),
                'limit': 1000,
                'remaining': max(0, 1000 - total_calls)
            }
        finally:
            session.close()

    def get_all_usage_stats(self):
        """Get usage statistics for all providers"""
        providers = ['omdb', 'tmdb', 'tvmaze']
        return {provider: self.get_usage_stats(provider) for provider in providers}

    # ============ SUGGESTED MATCHES OPERATIONS ============

    def save_suggested_match(self, file_path, file_name, match_data):
        """Save or update a suggested match for a file"""
        session = self.get_session()
        try:
            # Check if match already exists
            existing = session.query(SuggestedMatch).filter_by(file_path=file_path).first()

            if existing:
                # Update existing match
                existing.matched_title = match_data.get('title', '')
                existing.matched_year = match_data.get('year', '')
                existing.matched_imdb_id = match_data.get('imdb_id', '')
                existing.match_data = json.dumps(match_data)
                existing.updated_at = datetime.utcnow()
            else:
                # Create new match
                new_match = SuggestedMatch(
                    file_path=file_path,
                    file_name=file_name,
                    matched_title=match_data.get('title', ''),
                    matched_year=match_data.get('year', ''),
                    matched_imdb_id=match_data.get('imdb_id', ''),
                    match_data=json.dumps(match_data)
                )
                session.add(new_match)

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving suggested match: {e}")
            return False
        finally:
            session.close()

    def get_suggested_match(self, file_path):
        """Get suggested match for a specific file"""
        session = self.get_session()
        try:
            match = session.query(SuggestedMatch).filter_by(file_path=file_path).first()
            if match:
                return {
                    'file_path': match.file_path,
                    'file_name': match.file_name,
                    'matched_title': match.matched_title,
                    'matched_year': match.matched_year,
                    'matched_imdb_id': match.matched_imdb_id,
                    'match_data': json.loads(match.match_data) if match.match_data else {},
                    'created_at': match.created_at.isoformat(),
                    'updated_at': match.updated_at.isoformat()
                }
            return None
        finally:
            session.close()

    def get_suggested_matches_for_directory(self, directory):
        """Get all suggested matches for files in a directory"""
        session = self.get_session()
        try:
            matches = session.query(SuggestedMatch).filter(
                SuggestedMatch.file_path.like(f"{directory}%")
            ).all()

            return {
                match.file_path: json.loads(match.match_data) if match.match_data else {}
                for match in matches
            }
        finally:
            session.close()

    def delete_suggested_match(self, file_path):
        """Delete a suggested match for a file"""
        session = self.get_session()
        try:
            match = session.query(SuggestedMatch).filter_by(file_path=file_path).first()
            if match:
                session.delete(match)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting suggested match: {e}")
            return False
        finally:
            session.close()

    def clear_all_suggested_matches(self):
        """Clear all suggested matches"""
        session = self.get_session()
        try:
            session.query(SuggestedMatch).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error clearing suggested matches: {e}")
            return False
        finally:
            session.close()

    # ============ FOLDER RULES OPERATIONS ============

    def get_folder_rule(self, directory):
        """Get a folder rule for a specific directory"""
        session = self.get_session()
        try:
            rule = session.query(FolderRule).filter_by(directory=directory).first()
            if not rule:
                return None
            return {
                "directory": rule.directory,
                "preferred_source": rule.preferred_source,
                "insertion_position": rule.insertion_position,
                "language": rule.language,
                "subtitle_title_bold": rule.subtitle_title_bold,
                "subtitle_plot_italic": rule.subtitle_plot_italic,
                "subtitle_show_director": rule.subtitle_show_director,
                "subtitle_show_actors": rule.subtitle_show_actors,
                "subtitle_show_released": rule.subtitle_show_released,
                "subtitle_show_genre": rule.subtitle_show_genre,
            }
        finally:
            session.close()

    def get_all_folder_rules(self):
        """Get all folder rules"""
        session = self.get_session()
        try:
            rules = session.query(FolderRule).order_by(FolderRule.directory.asc()).all()
            return [
                {
                    "directory": rule.directory,
                    "preferred_source": rule.preferred_source,
                    "insertion_position": rule.insertion_position,
                    "language": rule.language,
                    "subtitle_title_bold": rule.subtitle_title_bold,
                    "subtitle_plot_italic": rule.subtitle_plot_italic,
                    "subtitle_show_director": rule.subtitle_show_director,
                    "subtitle_show_actors": rule.subtitle_show_actors,
                    "subtitle_show_released": rule.subtitle_show_released,
                    "subtitle_show_genre": rule.subtitle_show_genre,
                }
                for rule in rules
            ]
        finally:
            session.close()

    def upsert_folder_rule(self, directory, rule_data):
        """Create or update a folder rule"""
        session = self.get_session()
        try:
            rule = session.query(FolderRule).filter_by(directory=directory).first()
            if not rule:
                rule = FolderRule(directory=directory)
                session.add(rule)

            rule.preferred_source = rule_data.get("preferred_source")
            rule.insertion_position = rule_data.get("insertion_position")
            rule.language = rule_data.get("language")
            rule.subtitle_title_bold = rule_data.get("subtitle_title_bold")
            rule.subtitle_plot_italic = rule_data.get("subtitle_plot_italic")
            rule.subtitle_show_director = rule_data.get("subtitle_show_director")
            rule.subtitle_show_actors = rule_data.get("subtitle_show_actors")
            rule.subtitle_show_released = rule_data.get("subtitle_show_released")
            rule.subtitle_show_genre = rule_data.get("subtitle_show_genre")

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving folder rule: {e}")
            return False
        finally:
            session.close()

    def delete_folder_rule(self, directory):
        """Delete a folder rule for a directory"""
        session = self.get_session()
        try:
            rule = session.query(FolderRule).filter_by(directory=directory).first()
            if rule:
                session.delete(rule)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting folder rule: {e}")
            return False
        finally:
            session.close()

    # ============ MAINTENANCE OPERATIONS ============

    def clear_settings(self, keep_api_keys=False):
        """Clear all settings, optionally keeping API keys"""
        session = self.get_session()
        try:
            keep_values = {}
            if keep_api_keys:
                for key in ("omdb_api_key", "tmdb_api_key", "api_key"):
                    setting = session.query(Settings).filter_by(key=key).first()
                    if setting:
                        keep_values[key] = setting.value

            session.query(Settings).delete()
            session.commit()

            if keep_values:
                for key, value in keep_values.items():
                    session.add(Settings(key=key, value=value))
                session.commit()

            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error clearing settings: {e}")
            return False
        finally:
            session.close()

    def clear_history_and_logs(self):
        """Clear processing runs, scan history, scheduled scans, and API usage logs"""
        session = self.get_session()
        try:
            session.query(FileResult).delete()
            session.query(ProcessingRun).delete()
            session.query(ScanHistory).delete()
            session.query(ScheduledScan).delete()
            session.query(ApiUsage).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error clearing history and logs: {e}")
            return False
        finally:
            session.close()

    # ============ STATISTICS ============

    def get_statistics(self):
        """Get overall statistics"""
        session = self.get_session()
        try:
            total_runs = session.query(ProcessingRun).count()
            completed_runs = session.query(ProcessingRun).filter_by(status='completed').count()
            total_files_processed = session.query(FileResult).count()
            successful_files = session.query(FileResult).filter_by(success=True).count()

            return {
                'total_runs': total_runs,
                'completed_runs': completed_runs,
                'total_files_processed': total_files_processed,
                'successful_files': successful_files,
                'failed_files': total_files_processed - successful_files
            }
        finally:
            session.close()
