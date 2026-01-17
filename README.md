# Sublogue

Sublogue is a lightweight tool for adding plot summaries and metadata to subtitle files.

It takes an existing .srt, pulls data from OMDb, TMDb, and TVMaze, and inserts a short plot block at the start of the file — without altering any existing timings or dialogue.

If you’ve ever opened a movie or episode and thought “wait… what was this again?”, Sublogue quietly solves that.

## Features

- Inserts a plot summary at the beginning of an existing `.srt`
- Automatically fetches metadata (OMDb, TMDb, TVMaze fallback)
- Never alters existing dialogue timing
- Handles long plots without breaking readability
- Clean web UI (Svelte + Vite)
- Fast Python backend (Flask + aiohttp)
- Docker image available through GHCR

## Docker Compose

Create `data/` and `media/` folders next to the compose file, then run:

```yaml
version: "3.9"
services:
  sublogue:
    image: ponzischeme89/sublogue:latest
    container_name: sublogue
    restart: unless-stopped
    environment:
      - TZ=Etc/UTC
      - PUID=1000
      - PGID=1000
    volumes:
      - ./data:/config
      - ./media:/media
    ports:
      - "5000:5000"
```

Then start it with:

```bash
docker compose up -d
```

## Unraid

Sublogue includes an Unraid template at `unraid-sublogue.xml`. Import it in Unraid's Docker UI, then map:

- `/mnt/user/appdata/sublogue` -> `/config`
- `/mnt/user/appdata/sublogue/media` -> `/media`

Start the container and open `http://<UNRAID-IP>:5000`.

## Acknowledgements

- Svelte for the frontend UI.
- Flask for the backend API.
- asyncio for async metadata fetching.
