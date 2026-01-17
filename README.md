<div align="center">

  <img src="https://github.com/ponzischeme89/Sublogue/blob/master/docs/sublogue_logo.png" height="456" width="456">

  <h4>Your subtitles deserve metadata. Sublogue adds it.</h4>

</div>

Sublogue is a lightweight open-source tool for enriching SRT files. Pull metadata from OMDb, TMDB, or TVMaze and automatically append plot summaries, runtimes, directors, and cast details to the start or end of your subtitles. 

## Core Features
- Insert plot summaries into existing `.srt` files without shifting timings
- Fetch metadata from OMDb, TMDb, and TVMaze
- Add runtime, director, cast, and ratings to subtitle headers
- Preserve original dialogue and timing with safe insertion logic
- Clean, fast web UI for scanning and batch processing
- Docker-first deployment with persistent storage

## Getting started

### Docker

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

Start the stack:

```bash
docker compose up -d
```

Open `http://localhost:5000`.

### Unraid

Use the included template at `unraid-sublogue.xml`.

- `/mnt/user/appdata/sublogue` -> `/config`
- `/mnt/user/appdata/sublogue/media` -> `/media`

Start the container and open `http://<UNRAID-IP>:5000`.

### Komodo

Create a new stack and paste a Komodo template like this:

```yaml
version: "3.9"
services:
  sublogue:
    image: ponzischeme89/sublogue:latest
    container_name: sublogue

    ports:
      - "5000:5000"

    environment:
      - TZ=Etc/UTC
      - PUID=1000
      - PGID=1000

    volumes:
      - /volume1/Docker/sublogue/data:/config
      - /volume1/Media:/media

    restart: unless-stopped

    networks:
      - npm_network

networks:
  npm_network:
    external: true
```
