# Proposal: Local Web Control (Hotspot)

Control and monitor Astroflo from a phone/laptop by joining the Pi's Wi‑Fi hotspot and opening `http://astroflo.local` (or `http://10.42.0.1`). Mirrors and extends the TFT bonnet UI — it does not replace it.

## Goals
- View live camera frames, current solved coordinates, target and guidance (N/E offset).
- Search and set targets (stars, DSOs, solar system, raw RA/Dec).
- Edit **all** device settings (optics, camera, solver, environment, alignment).
- Take, list, view and download captures.
- Zero internet dependency; works offline in the field.

## Architecture

```
 Phone ──Wi‑Fi──► Pi hotspot (NetworkManager AP, 10.42.0.1)
                    │
                    ▼
            web/server.py  (FastAPI + uvicorn, port 80, own thread)
                    │  reads/writes
                    ▼
            ObservationContext  ◄── camera / solver / UI / analyzer threads
```

- New `web/` package started from `main.py` as one more thread, like `stel.run_server()`. Gets `ctx`, `catalog`, `camera`, `ui_state`.
- **FastAPI + uvicorn** (async, tiny, gives free `/docs` API explorer). Alternative: Flask if fewer deps preferred.
- Static frontend in `web/static/` — single `index.html` + vanilla JS, no build step, no CDN (offline).
- Live updates via **WebSocket** `/ws/state` pushing a JSON snapshot ~2 Hz; images via MJPEG `/stream` (or polled `/api/frame.jpg`).
- A shared `threading.Lock` on `ObservationContext` for writes from the web thread (state is currently mutated lock‑free).

## Hotspot setup (Pi)
```
sudo nmcli dev wifi hotspot ifname wlan0 ssid Astroflo password <pw>
sudo nmcli con modify Hotspot connection.autoconnect yes
```
Plus `avahi-daemon` for `astroflo.local`. Document in `build/SETUP.md`. Optional: fall back to client mode if a known network is found.

## API

| Method | Path | Purpose |
|---|---|---|
| GET  | `/api/state` | Snapshot: position (RA/Dec + Alt/Az), roll, solved?, last_solved age, target, N/E offset & distance, FWHM, camera exposure/gain, screen |
| WS   | `/ws/state` | Same snapshot, pushed |
| GET  | `/stream` | MJPEG of `camera_state.latest_image` |
| GET  | `/api/frame.jpg?overlay=1` | Latest frame, optional target‑pixel / star overlay |
| GET  | `/api/starfield.png` | Rendered `StarfieldRenderer` view |
| GET  | `/api/targets?type=stars\|dsos\|solar&mag=6&q=m31&visible=1` | Catalog search (wraps `get_bright_stars`, `get_dsos`, `get_solar_system`, `search_by_name`) |
| POST | `/api/target` | `{name}` or `{ra, dec, name}`; DELETE clears |
| GET/PUT | `/api/settings` | All settings (below), validated, persisted |
| POST | `/api/capture` | Save current frame (optionally high‑res still) → returns id |
| GET  | `/api/captures` | List with timestamp, exposure, gain, solve result |
| GET/DELETE | `/api/captures/{id}` | View/download/delete |
| POST | `/api/alignment` | Set target pixel `{x,y}` (click on frame) → `solver_state.save_offset` |
| POST | `/api/camera` | `{enabled, exposure, gain, profile}` → `camera.configure` |
| POST | `/api/system/{restart\|shutdown}` | Service restart / Pi shutdown (confirm in UI) |

## Settings covered

| Group | Fields | Source today |
|---|---|---|
| Optics | focal_length, aperture, eyepiece, eyepiece_fov, zoom | `TelescopeOptics` / `settings.txt` |
| Camera | enabled, exposure, gain, profile (`ExposureProfile`/`GainProfile`), save frames, fake_image_test | `CameraState`, `Camera` |
| Solver | fov estimate, target pixel (x,y), solver choice | `SolverState`, `offset.npy` |
| Alignment | x_offset, y_offset, view_angle | `settings.txt` |
| Environment | lat, lon, elevation, min_visible_altitude, time override | hard‑coded Rochester in `observation_context.py` |
| Integrations | Stellarium server on/off + port, coordinate logging | `StellariumConnection`, `TelescopeState.logging` |
| Display | sky drift sim, TFT screen state | `main.py`, `UIState` |

**Prerequisite refactor:** `settings.txt` is currently not read anywhere and location is hard‑coded. Introduce `config.py` with a dataclass loaded from/saved to `settings.json` (migrate `settings.txt` + `offset.npy`), applied to `ObservationContext` on boot and on `PUT /api/settings`.

## UI pages (single page, tabbed, mobile‑first, red/dark night mode)
1. **Live** — stream, overlay toggle, RA/Dec/Alt/Az, solve status/age, target + arrow and distance (reuse `distance_north_east`), FWHM sparkline for focus.
2. **Targets** — tabs Stars/DSOs/Solar/Coords, search, mag slider, "visible only", tap to set; current target pinned.
3. **Captures** — "Take image" button, gallery grid, detail with metadata + download.
4. **Align** — tap frame to set target pixel, nudge buttons, save.
5. **Settings** — grouped forms per table above, Save / Revert, system restart/shutdown.

## Implementation plan
1. `config.py` + settings persistence; wire into `ObservationContext` (no behaviour change).
2. Context lock + `snapshot()` method returning JSON‑serialisable state.
3. `web/server.py` with read‑only endpoints (`/api/state`, `/stream`, `/ws/state`) + Live page.
4. Targets endpoints + page.
5. Captures: timestamped saves in `captures/` with sidecar JSON metadata (replace overwrite of `latest.jpg`) + page.
6. Settings + Align + system endpoints/pages.
7. Hotspot/avahi/systemd docs in `build/SETUP.md`; add `fastapi`, `uvicorn` to `requirements.txt`.
8. Tests with FastAPI `TestClient` using `FakeCamera`/`FakeSolver` (already work off‑Pi).

## Risks / notes
- **CPU on Pi**: JPEG encode per frame — cap stream to ~2 fps, downscale, encode only when a client is connected.
- **Thread safety**: web writes race UI/solver; lock + atomic target swap.
- **Security**: hotspot is WPA2‑protected; optional PIN for shutdown/settings. Bind only to the hotspot interface.
- **Port 80** needs root or `CAP_NET_BIND_SERVICE`; else use 8080.
- Existing bugs to fix along the way: `TelescopeState._log_coordinates` references `self.scope`; `CatalogType` values are tuples while `TargetSelect` matches ints.

## Open questions
- FastAPI vs Flask?
- Should the web UI be able to change the TFT screen, or stay independent?
- Keep all captures or ring‑buffer (SD card space)?
