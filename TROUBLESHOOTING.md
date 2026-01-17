# Troubleshooting

- Permissions denied: set `PUID`/`PGID` correctly and run `chown -R` on your host folders.
- Port conflicts: change host port mapping (e.g., `5001:5000`).
- Missing network: create `npm_network` with `docker network create npm_network`.
- Reverse proxy not working: verify NPM is on the same network and forward to `sublogue:5000`.
- Healthcheck failing: confirm the app is listening on port `5000` and `/api/health` returns OK.
- No metadata results: ensure at least one integration is enabled in Settings.
