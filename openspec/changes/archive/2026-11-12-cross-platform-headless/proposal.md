# Proposal

## Why

astroflo only runs end to end on the Raspberry Pi: hardware is chosen by checking whether the hostname is `rpi`, the solver loads from hard-coded home-directory paths, the off-Pi finder camera repeats one fixed image, the UI draw loop exits immediately on any other machine, and the test suite has no CI and no rules for when hardware tests should be skipped. Development and review on Windows, macOS or a headless Linux box (CI, cloud containers) therefore covers only part of the app. Making every non-hardware path run anywhere, fed by recorded test images, lets most bugs be caught before code reaches the Pi.

## What Changes

- Add one explicit runtime profile (`pi` / `sim`), chosen by a setting or environment variable, with hostname detection kept only as the default. Each hardware piece (finder camera, imaging camera, solver, display, buttons) gets its own backend choice so a Pi can also run partly simulated.
- Add a **simulated finder camera** that replays images from a folder (default `test_data/`), in order or looped, with optional per-image delay, in place of the single hard-coded `out_of_focus.jpg`.
- Let the **fake imaging camera** take frames from a folder of test images (scaled by exposure/gain) as well as producing synthetic frames.
- Add a **headless virtual display**: the full UI render loop runs off-Pi and keeps the latest frame in memory (and optionally writes PNG snapshots), so screens are exercised without a physical TFT.
- Add **simulated button input**: scripted or programmatic press/release/hold events through the existing `Input` interface, also usable from the web UI and from tests.
- Add a solver choice: `fake` (current behavior), `tetra3` (pure Python, runs on any OS against test images), `cedar` (Pi only). Cedar paths come from settings/env instead of `/home/owen/...` or `C:/Users/...`.
- Make startup cross-platform: no `os.uname()` on Windows, no Linux-only font paths, Agg/headless matplotlib backend selectable through `MPLBACKEND`, a clear message instead of a crash when ephemeris data is missing, and `sudo systemctl`/`reboot` system actions rejected with a clear error off Linux.
- Split dependencies: core requirements that install on Windows/macOS/Linux, plus `requirements_pi.txt` and optional extras (Cedar, tetra3) so `pip install` never needs Pi-only or Git-only packages to run the simulation.
- Add **pytest markers and conditional skips** (`linux_only`, `pi_only`, `requires_camera`, `requires_v4l2`, `requires_tetra3`, `requires_ephemeris`) with detection in `conftest.py`. Tests assume no camera is present unless one is detected.
- Expand test coverage over everything that is not hardware: settings, rendering of every screen, input navigation, simulated cameras, solver pipeline on test images, web API, and an end-to-end headless smoke run of `main`.
- Add a GitHub Actions matrix (ubuntu, windows, macos × supported Python versions) that runs the suite headless.

No **BREAKING** changes: on the Pi, default behavior stays the same.

## Capabilities

### New Capabilities
- `runtime-platform`: how astroflo picks its runtime profile and hardware backends, and what it guarantees about starting and running on Linux, macOS and Windows with no camera or screen attached.
- `hardware-simulation`: simulated finder camera, imaging camera from test images, headless virtual display and simulated button input, used for development and tests.
- `test-suite`: how tests are grouped by platform and hardware need, the conditional-skip rules, coverage expectations and the CI matrix.

### Modified Capabilities
<!-- None: imaging-camera, imaging-ui and image-storage requirements stay as they are; their tests run on every platform through the fake backends. -->

## Impact

- **Code**: `utils.py` (`is_pi`), `main.py` (backend builders), `config.py` (new `runtime`/`solver`/`finder_camera.source` settings), `hardware/adafruit_tft_bonnet.py`, `hardware/ui.py`, `hardware/input.py`, `capture/fake_camera.py`, `capture/fake_imaging_camera.py`, `solve/cedar.py`, new `solve/tetra3_solver.py`, `astronomy/catalog.py` (missing-data handling), `web/server.py` (system actions, sim input endpoint), `web/dev_server.py` (may be merged into `main --sim`).
- **Tests**: `tests/conftest.py` (markers, platform detection), new test modules; existing tests get markers where needed.
- **Dependencies**: `requirements.txt` split into core + optional; `pytest`, `httpx`, `pydantic` declared explicitly.
- **CI**: new `.github/workflows/tests.yml`.
- **Docs**: `build/SETUP.md` section on running on Windows/macOS/Linux in sim mode.
