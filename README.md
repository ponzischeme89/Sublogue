<div align="center">

  <img src="https://github.com/ponzischeme89/Sublogue/blob/master/docs/sublogue_v2.png" height="256" width="456">

  <h4>Your subtitles deserve metadata. Sublogue adds it.</h4>

</div>

Sublogue is a lightweight open-source tool for enriching SRT files. Pull metadata from OMDb, TMDB, or TVMaze and automatically append plot summaries, runtimes, directors, and cast details to the start or end of your subtitles. 

Why? If the cast and IMDb/RT rating appear in the first minute, movie night involves fewer questions and more watching!

## Core Features
- Insert plot summaries into existing `.srt` files without shifting timings
- Fetch metadata from OMDb, TMDb, and TVMaze
- Add runtime, director, cast, and ratings to subtitle headers
- Preserve original dialogue and timing with safe insertion logic
- Clean, fast web UI for scanning and batch processing built in Svelte


## Screenshots
<div align="center">

  <img src="https://github.com/ponzischeme89/Sublogue/blob/master/docs/screenshots/screenshot_main.png" height="256" width="456">
  <img src="https://github.com/ponzischeme89/Sublogue/blob/master/docs/screenshots/screenshot_settings.png" height="256" width="456">

</div>

## Getting started

<details>
<summary>⚓ Docker Compose</summary>
Create `data/` and `media/` folders next to the compose file, then run:

```yaml
version: "3.9"
services:
  sublogue:
    image: ghcr.io/ponzischeme89/sublogue:latest
    container_name: sublogue
    restart: unless-stopped
    environment:
      - TZ=Pacific/Auckland
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
</details>
<details>
  <summary>🧡 Unraid</summary>

Use the included template at `unraid-sublogue.xml`.

- `/mnt/user/appdata/sublogue` -> `/config`
- `/mnt/user/appdata/sublogue/media` -> `/media`

Start the container and open `http://<UNRAID-IP>:5000`.
</details>

<details>
<summary>🦎 Komodo</summary>

Create a new stack and paste a Komodo template like this:

```yaml
version: "3.9"
services:
  sublogue:
    image: ghcr.io/ponzischeme89/sublogue:latest
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
</details>

## Support
- Help spread the word about Sublogue by telling your friends about this repo
- Give the repo a star (This really helps)
