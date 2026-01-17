# Sublogue

Sublogue is a small, fast tool for adding plot summaries and metadata to subtitle files.  
Built in New Zealand for people who like tidy media libraries and clean viewing experiences.

It takes an existing `.srt` file, fetches metadata from OMDb/TMDb and TVMaze, and inserts a short plot block at the start of the file — without touching any existing timings or shifting dialogue.

If you’ve ever opened a movie and forgotten what it’s about, this fixes that.

---

## Features

- Inserts a plot summary at the beginning of an existing `.srt`
- Automatically fetches metadata (OMDb, TMDb, TVMaze fallback)
- Never alters existing dialogue timing
- Handles long plots without breaking readability
- Clean web UI (Svelte + Vite)
- Fast Python backend (Flask + aiohttp)
- Docker image available through GHCR

---