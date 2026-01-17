# Sublogue Installation Guide

## Synology
- Create folders: `./data` and `./media` (or map to Synology shared folders).
- In Container Manager, create a project and paste `docker-compose.yml`.
- Map volumes to your shared folders (e.g., `/volume1/docker/sublogue` -> `/config`, `/volume1/media` -> `/media`).
- Start the stack, then open `http://<NAS-IP>:5000`.

## Unraid
- Create folders: `/mnt/user/appdata/sublogue` and `/mnt/user/appdata/sublogue/media`.
- Add the container using `unraid-sublogue.xml` or import `docker-compose.yml` with a compose manager.
- Set `TZ`, `PUID`, `PGID` to match your Unraid user (often `99/100`).
- Start the container, open `http://<UNRAID-IP>:5000`.

## Komodo
- Add a new stack and paste `docker-compose.yml`.
- Ensure the `npm_network` exists (`docker network create npm_network`).
- Deploy and open `http://<HOST-IP>:5000`.

## Portainer
- Stacks -> Add Stack -> Web editor -> paste `docker-compose.yml`.
- Ensure `npm_network` exists if you are using the proxy compose.
- Deploy and open `http://<HOST-IP>:5000`.

## Bare Metal Docker CLI
- Create folders: `mkdir -p ./data ./media`.
- Run: `docker compose up -d`.
- Open: `http://<HOST-IP>:5000`.

## Folder Structure
- `./data` -> container `/config` (database and settings).
- `./media` -> container `/media` (media library access).
- For NPM: `./npm/data` and `./npm/letsencrypt`.

## Permissions (chmod/chown)
- If you see permission errors, set `PUID`/`PGID` to your host user ID.
- Fix ownership: `sudo chown -R 1000:1000 ./data ./media`.
- Fix permissions: `sudo chmod -R 775 ./data ./media`.

## Updates
- Watchtower (auto): run `containrrr/watchtower:latest` with `WATCHTOWER_CLEANUP=true`.
- Manual update:
  - `docker compose pull`
  - `docker compose up -d`

## Nginx Proxy Manager (NPM)
- Use `docker-compose.proxy.yml`.
- In NPM, add a proxy host for your domain -> forward to `sublogue:5000`.
- Enable SSL and Let’s Encrypt in NPM (auto-renewal is handled by NPM).
- Advanced config (headers):
  - `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`
  - `proxy_set_header X-Forwarded-Proto $scheme;`
  - `proxy_set_header X-Forwarded-Host $host;`
  - `proxy_set_header X-Forwarded-Port $server_port;`
