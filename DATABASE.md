# SubPlotter Database

SubPlotter uses SQLite with SQLAlchemy for persistent data storage.

## Database File

The database is stored in `subplotter.db` in the application root directory.

## Tables

### Settings
Stores application configuration (API key, default directory, duration, etc.)

**Columns:**
- `id` (Integer, Primary Key)
- `key` (String, Unique, Indexed) - Setting name
- `value` (Text) - Setting value (JSON encoded)
- `updated_at` (DateTime) - Last update timestamp

### ProcessingRun
Tracks each batch processing session

**Columns:**
- `id` (Integer, Primary Key)
- `started_at` (DateTime, Indexed) - When processing started
- `completed_at` (DateTime) - When processing completed
- `total_files` (Integer) - Total files in this run
- `successful_files` (Integer) - Successfully processed files
- `failed_files` (Integer) - Failed files
- `duration_seconds` (Float) - Total processing time
- `status` (String) - Run status: 'in_progress', 'completed', 'failed'

### FileResult
Stores individual file processing results

**Columns:**
- `id` (Integer, Primary Key)
- `run_id` (Integer, Foreign Key to ProcessingRun)
- `file_path` (String, Indexed) - Full path to file
- `file_name` (String) - Just the filename
- `success` (Boolean) - Whether processing succeeded
- `status` (String) - Status message
- `summary` (Text) - Plot summary added
- `error_message` (Text) - Error details if failed
- `processed_at` (DateTime) - When file was processed
- `duration` (Integer) - Subtitle duration in seconds

### ScanHistory
Tracks directory scan history

**Columns:**
- `id` (Integer, Primary Key)
- `directory` (String, Indexed) - Directory path scanned
- `scanned_at` (DateTime, Indexed) - When scan occurred
- `files_found` (Integer) - Number of SRT files found
- `files_with_plot` (Integer) - Files that already have plot summaries
- `scan_duration_ms` (Integer) - How long the scan took in milliseconds

## API Endpoints

### History Endpoints

**GET /api/history/runs?limit=50**
Get list of processing runs
```json
{
  "success": true,
  "runs": [
    {
      "id": 1,
      "started_at": "2024-01-01T12:00:00",
      "completed_at": "2024-01-01T12:05:00",
      "total_files": 10,
      "successful_files": 8,
      "failed_files": 2,
      "duration_seconds": 300.5,
      "status": "completed"
    }
  ]
}
```

**GET /api/history/runs/{run_id}**
Get detailed information about a specific run including all file results
```json
{
  "success": true,
  "run": {
    "id": 1,
    "started_at": "2024-01-01T12:00:00",
    "completed_at": "2024-01-01T12:05:00",
    "total_files": 10,
    "successful_files": 8,
    "failed_files": 2,
    "duration_seconds": 300.5,
    "status": "completed",
    "file_results": [
      {
        "id": 1,
        "file_path": "/path/to/movie.srt",
        "file_name": "movie.srt",
        "success": true,
        "status": "Plot added successfully",
        "summary": "A hero saves the day...",
        "error_message": null,
        "processed_at": "2024-01-01T12:00:30",
        "duration": 40
      }
    ]
  }
}
```

**GET /api/history/scans?limit=50**
Get scan history
```json
{
  "success": true,
  "scans": [
    {
      "id": 1,
      "directory": "C:\\Movies",
      "scanned_at": "2024-01-01T12:00:00",
      "files_found": 25,
      "files_with_plot": 10,
      "scan_duration_ms": 150
    }
  ]
}
```

**GET /api/statistics**
Get overall statistics
```json
{
  "success": true,
  "statistics": {
    "total_runs": 50,
    "completed_runs": 48,
    "total_files_processed": 500,
    "successful_files": 450,
    "failed_files": 50
  }
}
```

## Migration

On first startup, SubPlotter automatically migrates settings from the legacy `settings.json` file to the database. The JSON file is kept for backward compatibility but all new settings are stored in the database.

## Database Manager Usage

```python
from core.database import DatabaseManager

# Initialize
db = DatabaseManager("subplotter.db")

# Settings operations
db.set_setting("api_key", "your-key")
api_key = db.get_setting("api_key", "")
all_settings = db.get_all_settings()

# Create a processing run
run_id = db.create_run(total_files=10)

# Add file results
db.add_file_result(
    run_id=run_id,
    file_path="/path/to/movie.srt",
    success=True,
    status="Plot added",
    summary="A hero...",
    duration=40
)

# Complete the run
db.complete_run(run_id, successful_files=8, failed_files=2)

# Query history
runs = db.get_run_history(limit=50)
run_details = db.get_run_details(run_id)

# Add scan history
db.add_scan_history(
    directory="/path/to/movies",
    files_found=25,
    files_with_plot=10,
    scan_duration_ms=150
)

# Get statistics
stats = db.get_statistics()
```

## Backup

The SQLite database file can be backed up simply by copying `subplotter.db` to a safe location.

## Reset Database

To reset the database, simply delete `subplotter.db` and restart the application. A new database will be created automatically.
