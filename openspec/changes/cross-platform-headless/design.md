# Design

## Context

See proposal.md – Why. Current state that shapes the approach:

- `utils.is_pi()` (hostname == `rpi`) is the only switch. `main.build_*` and `hardware/adafruit_tft_bonnet.py` branch on it at import time; `hardware/ui.py:draw_screen` returns at once off-Pi, so screens are only rendered on demand by the web server.
- Simulated pieces already exist but are minimal: `FakeCamera` (one in-memory image), `FakeImagingCamera` (synthetic noise), `FakeSolver` (fixed Pleiades position), a no-op fake TFT. `web/dev_server.py` builds a separate, partly duplicated sim stack.
- `solve/cedar.py` inserts `/home/owen/cedar-solve` or `C:/Users/314ow/cedar-solve` into `sys.path`; `solve/astrometry_handler.py` shells out through WSL on Windows.
- `Catalog.load()` calls skyfield `load()` on gitignored `.bsp` files; with the file missing skyfield tries to download it.
- `web/server.py` system actions call `sudo systemctl/reboot/shutdown` on any OS.
- `requirements.txt` mixes core packages with `git+…tetra3`, `grpcio`, `google`; `pytest` is listed but `pydantic`/`astropy` are not (pulled in transitively).
- Tests (`tests/*.py`) use fakes and stubs and have no markers, no CI.

## Goals / Non-Goals

**Goals:**
- One code path for building the app (`main.py`) in both profiles; `web/dev_server.py` becomes a thin wrapper or is removed.
- No import of Pi-only modules (`board`, `digitalio`, `picamera2`, Cedar) unless that backend is selected.
- Tests that are fast (no real exposure sleeps), deterministic (seeded noise) and isolated (tmp dirs).

**Non-Goals:**
- Running Cedar-detect, `picamera2`, GPIO or the SV105 V4L2 path on Windows/macOS.
- A desktop GUI window for the virtual display (the web UI already shows the screen).
- Supporting astrometry.net on non-Linux beyond what exists today (WSL path stays as is, not tested in CI).
- Packaging (wheels, installers).

## Decisions

### D1. Profile + backend registry in settings
Add a `RuntimeSettings` section to `config.Settings`:
```
runtime:
  profile: auto | pi | sim
  finder_camera: auto | rpi | images
  imaging_camera: auto | sv105 | fake | alpaca | uvc | none
  solver: auto | fake | tetra3 | cedar
  display: auto | tft | virtual
  input: auto | gpio | sim
```
`auto` resolves from the profile. Resolution order for profile: `ASTROFLO_PROFILE` env → settings → `is_pi()`. A new `platform_info.py` module holds `resolve_profile()`, `is_pi()`, `is_linux()/is_macos()/is_windows()` and capability probes (`has_v4l2_ctl`, `has_module(name)`); `utils.is_pi` re-exports for compatibility and is fixed to use `platform.node()` (works on Windows).
Backends live in a small registry (`backends.py`) mapping name → (factory, `available()` check). An unavailable explicit choice raises with a reason (spec: no silent fallback).
*Alternatives:* CLI flags only (not persisted, awkward for the Pi service); keep hostname check (no way to force sim on Pi or real solver on laptop).
*Note:* the existing `imaging_camera.backend` setting (used by the web remote imaging controller) is kept; `runtime.imaging_camera` covers the on-device `ImagingController`. Merging the two is left for later.

### D2. Lazy hardware imports
Split `hardware/adafruit_tft_bonnet.py` into `hardware/tft_display.py` (real; imports `board` etc. inside the module, only imported by its factory) and `hardware/virtual_display.py`. Both implement a `Display` protocol: `set_brightness`, `set_backlight`, `clear`, `draw_screen(img)`, `read_buttons(input)`. Fonts come from `matplotlib.font_manager` (already used by `renderer.py`) rather than `/usr/share/fonts/...`.
`UIManager.draw_screen` loops in every profile; virtual display stores `latest_frame` (+ lock) and optionally writes PNGs (`ASTROFLO_SNAPSHOT_DIR`, throttled).

### D3. Image-folder finder camera
Extend `FakeCamera` into `ImageFolderCamera(source, loop=True, simulate_exposure=True)`: accepts a file or directory, sorts by name, loads lazily via Pillow, converts to RGB `uint8`. Default source `test_data/`. Falls back to seeded noise frames with a warning when empty. Also fixes the existing double `queue.put` (in both `capture()` and `capturer()`).

### D4. Imaging camera from images
`FakeImagingCamera(source=None, seed=None)`: when `source` set, cycles images converted to grayscale/float, multiplies by `exposure_s * gain_factor / reference_exposure`, adds seeded noise, clips. Synthetic mode unchanged.

### D5. Simulated input
`SimInput` queue feeding the existing `Input.update()` from the input thread: `press(button)`, `release(button)`, `tap(button)`, `hold(button, seconds)`, `run_script("D A wait:0.5 B")`. Web: `POST /api/sim/input {button, action}` registered only when input backend is `sim` (otherwise 409). Tests call `SimInput` directly, without threads, via a `step()` method.

### D6. Solvers
- `FakeSolver`: target position from constructor/settings instead of a class attribute.
- New `solve/tetra3_solver.py`: uses the `tetra3` pip package with its bundled database and built-in centroiding; marked optional.
- `CedarSolver`: path from `ASTROFLO_CEDAR_PATH` / settings, imported only when selected; `available()` checks the import and the `cedar-detect-server` binary.

### D7. Cross-platform hygiene
- `matplotlib`: honor `MPLBACKEND` if set; else Agg on all OSes when the display backend is virtual (the existing Windows comment refers to interactive use; Agg is thread-safe for off-screen rendering — verify in CI on Windows).
- `Catalog`: check files exist before `skyfield.load`; missing → features disabled + message. Construct with `Loader(directory, verbose=False)` and never download implicitly.
- `web/server.py` system actions: `if not is_linux(): 501`.
- Paths: use `os.path.join`/`pathlib` everywhere; open text with `encoding="utf-8"`.
- `main.py`: add `--profile`, `--duration SECONDS`, `--no-web` args; threads become daemon threads with a shared `stop_event`, so Ctrl+C and duration limits exit within 5 s.

### D8. Dependencies
- `requirements.txt` → core, installable on all three OSes from PyPI wheels: numpy, scipy, Pillow, opencv-python-headless, matplotlib, astropy, skyfield, photutils, pydantic, pytz, requests, fastapi, uvicorn, websockets, alpyca.
- `requirements-dev.txt`: `-r requirements.txt`, pytest, httpx, pytest-timeout.
- `requirements-solver.txt`: tetra3 (git), grpcio, protobuf (Cedar client).
- `requirements_pi.txt`: unchanged plus `-r requirements.txt` and Adafruit packages (`adafruit-circuitpython-rgb-display`, `adafruit-blinka`) that are currently undeclared.
- `google`, `mahotas` and `starplot` have no imports in the repo (checked): drop `google`, move the other two out of core.

### D9. Test markers and detection
In `tests/conftest.py` register markers and a `pytest_collection_modifyitems` hook:

| marker | runs when |
|---|---|
| `linux_only` / `macos_only` / `windows_only` | `sys.platform` matches |
| `pi_only` | `platform_info.is_pi()` |
| `requires_camera` | `ASTROFLO_HW_TESTS=1` **and** a camera is detected (finder: `picamera2` importable + device; imaging: SV105 found) |
| `requires_v4l2` | Linux and `v4l2-ctl` on PATH |
| `requires_tetra3` | `tetra3` importable |
| `requires_ephemeris` | `data/de440s.bsp` present |
| `slow` | always, but deselectable with `-m "not slow"` |

Camera detection is opt-in (`ASTROFLO_HW_TESTS`) so a laptop webcam is never mistaken for hardware (spec: assume no camera). Skip reasons are the marker's text. Autouse fixtures: seed `numpy.random`, set `MPLBACKEND=Agg`, redirect `BASE_DIR`-relative writes (`captures/`, `saves/`, `settings.json`, `offset.npy`, `coord_log.txt`) to `tmp_path` via monkeypatching module constants.

New/expanded test modules: `test_platform.py` (profile resolution, backend availability errors), `test_sim_cameras.py`, `test_virtual_display.py`, `test_sim_input.py` (menu navigation for every screen), `test_screens_render.py` (parametrized over `ScreenState`), `test_solver_pipeline.py` (fake + tetra3), `test_catalog.py` (missing data + real data with `requires_ephemeris`), `test_web.py` (sim input, system action rejection), `test_smoke.py` (`python main.py --profile sim --duration 8` in a subprocess, `slow`), `test_hardware.py` (`pi_only`/`requires_camera` real-device checks moved from `tools/sv105_probe.py` logic).

### D10. CI
`.github/workflows/tests.yml`: matrix `os: [ubuntu-latest, macos-latest, windows-latest]`, `python: ["3.11", "3.13"]`; `pip install -r requirements-dev.txt`; `pytest -rs --timeout=120`. A second job on ubuntu also installs `requirements-solver.txt` to run `requires_tetra3` tests. Ephemeris-dependent tests stay skipped in CI unless the file is cached (optional follow-up).

## Risks / Trade-offs

- [Agg on Windows threads previously reported unstable] → Keep the `MPLBACKEND` override; CI on Windows runs the smoke test; render calls already go through `StarfieldRenderer`'s lock.
- [tetra3 install from Git is slow/fragile] → Only in the optional solver job; core suite never needs it.
- [No recorded star-field image with known coordinates in `test_data/`] → Add one small image with its expected RA/Dec to `test_data/` (or generate a synthetic field from the Tycho catalog) for the tetra3 test.
- [`opencv-python` → `-headless` swap on the Pi] → Pi keeps whatever `requirements_pi.txt` pins; both provide `cv2`.
- [Moving tests' file writes to tmp needs module constants to be patchable] → Prefer constructor/`path` arguments (as `SettingsStore` and `CaptureStore` already do) over monkeypatching where possible.
- [Real-hardware behavior can diverge from simulation] → `pi_only`/`requires_camera` tests kept and run on the Pi with `ASTROFLO_HW_TESTS=1`.

## Migration Plan

1. Land platform module, settings and lazy imports with `auto` defaults: Pi behavior unchanged.
2. Land simulation backends and `main` args; remove or slim `web/dev_server.py`.
3. Split requirements; update `build/SETUP.md`.
4. Add markers, new tests, CI.
Rollback: settings default to `auto`, so reverting any step restores current behavior; unknown `runtime` keys in `settings.json` are ignored by older code (pydantic default `extra="ignore"`).

## Open Questions

- Which Python versions should CI cover beyond 3.11 and 3.13 (does the Pi run 3.11)? Can be adjusted in the workflow later.
- Whether to cache `de440s.bsp` in CI to run ephemeris tests there.
