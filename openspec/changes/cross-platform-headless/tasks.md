# Tasks

## 1. Dependencies and test scaffolding

- [ ] 1.1 Split requirements into `requirements.txt` (core, PyPI wheels only, `opencv-python-headless`, explicit `pydantic`/`astropy`), `requirements-dev.txt`, `requirements-solver.txt`, and update `requirements_pi.txt` (adds Adafruit packages, `-r requirements.txt`); verify `pip install -r requirements-dev.txt` succeeds in a fresh venv and `python -c "import main"` does not fail on a missing package
- [ ] 1.2 Add `platform_info.py` (`is_pi` via `platform.node()`, `is_linux/is_macos/is_windows`, `has_module`, `has_v4l2_ctl`) and make `utils.is_pi` re-export it; verify with new `tests/test_platform.py` using monkeypatched `sys.platform`/`platform.node`
- [ ] 1.3 Register markers (`linux_only`, `macos_only`, `windows_only`, `pi_only`, `requires_camera`, `requires_v4l2`, `requires_tetra3`, `requires_ephemeris`, `slow`) and the skip hook in `tests/conftest.py`, plus autouse fixtures (seeded RNG, `MPLBACKEND=Agg`); verify `pytest -rs` shows the right skip reasons for a dummy test of each marker on this OS
- [ ] 1.4 Add a test-isolation fixture that points settings, `offset.npy`, `coord_log.txt`, `captures/` and `saves/` at `tmp_path`; verify `git status` is clean after `pytest`
- [ ] 1.5 Mark existing tests where needed (none should need hardware; `test_imaging_cameras` parsers stay unmarked) and verify the existing suite passes with `pytest -rs`

## 2. Runtime profile and backend selection

- [ ] 2.1 Add `RuntimeSettings` (`profile`, `finder_camera`, `imaging_camera`, `solver`, `display`, `input`) to `config.Settings` with `auto` defaults; verify old `settings.json` files still load and new keys round-trip in `tests/test_web.py::test_settings_apply_and_persist`
- [ ] 2.2 Implement `resolve_profile()` (env → settings → `is_pi`) with an error listing allowed values on bad input, and print the chosen profile at startup; verify in `tests/test_platform.py`
- [ ] 2.3 Add `backends.py` registry with `available()` checks and explicit error on unavailable choice (no silent fallback); refactor `main.build_camera/build_imaging_camera/build_solver` to use it; verify by tests for `sim` defaults, `pi` defaults (factories stubbed), and an unavailable backend raising a message naming it
- [ ] 2.4 Add `main.py` args `--profile`, `--duration`, `--no-web`; convert threads to daemon threads sharing a `stop_event`; verify `python main.py --profile sim --duration 5 --no-web` exits 0 within ~10 s on this machine
- [ ] 2.5 Document profiles, backends and env vars in `build/SETUP.md` ("Running without hardware on Windows/macOS/Linux"); verify the documented commands run as written

## 3. Simulated cameras

- [ ] 3.1 Replace `FakeCamera` with an image-folder finder camera (file or folder source, name order, loop, RGB `uint8`, noise fallback with warning, `simulate_exposure` flag) and remove the double `queue.put`; verify with `tests/test_sim_cameras.py` (order/loop, single file, empty folder, fast mode, one queue item per capture)
- [ ] 3.2 Add `finder_camera.source` setting (default `test_data/`) wired through the backend registry; verify a settings override changes the replayed images in a test
- [ ] 3.3 Extend `FakeImagingCamera` with an optional image source and seed (brightness scaled by exposure/gain, unplug still works); verify brightness-vs-exposure and unplug tests in `tests/test_sim_cameras.py`, and existing `tests/test_imaging_controller.py` still passes

## 4. Headless display and simulated input

- [ ] 4.1 Split `hardware/adafruit_tft_bonnet.py` into a lazily imported `tft_display.py` and a `virtual_display.py` behind a common display interface; use the matplotlib font instead of `/usr/share/fonts/...`; verify `import hardware.ui` works on non-Pi without `board`/`digitalio` installed
- [ ] 4.2 Make `UIManager.draw_screen` loop in every profile, storing `latest_frame` in the virtual display with optional throttled PNG snapshots (`ASTROFLO_SNAPSHOT_DIR`); verify with `tests/test_virtual_display.py` (frame is 240×240, snapshots written to tmp, display-off stops rendering)
- [ ] 4.3 Add `SimInput` (press/release/tap/hold/script, `step()` for tests) feeding `Input.update`; verify with `tests/test_sim_input.py` navigating from main menu to every reachable screen and back
- [ ] 4.4 Add `tests/test_screens_render.py` parametrized over every `ScreenState`, rendering each with fake context; verify all produce a 240×240 image without error
- [ ] 4.5 Add `POST /api/sim/input` (409 unless input backend is `sim`) and have the web screen stream use the virtual display's latest frame when present; verify new cases in `tests/test_web.py`

## 5. Solvers and data files

- [ ] 5.1 Make `FakeSolver` target configurable (constructor/settings) instead of a class attribute; verify in `tests/test_solver_pipeline.py` that finder frames → solver → `telescope_state.position` updates
- [ ] 5.2 Make `CedarSolver` read its path from `ASTROFLO_CEDAR_PATH`/settings, import only when selected, and report unavailability clearly; verify the backend check returns "not available" off-Pi in `tests/test_platform.py`
- [ ] 5.3 Add `solve/tetra3_solver.py` and a recorded star-field test image with known RA/Dec in `test_data/`; verify a `requires_tetra3` test solves it within 1°
- [ ] 5.4 Guard `Catalog` against missing `.bsp`/FITS files (no implicit download, planets disabled, message names the file); verify with `tests/test_catalog.py` (missing-file case unmarked, real-data case `requires_ephemeris`)

## 6. Cross-platform hygiene

- [ ] 6.1 Reject `/api/system/*` with 501 off Linux without running any command; verify a `tests/test_web.py` case with `is_linux` patched to False, and that `subprocess.Popen` is not called
- [ ] 6.2 Honor `MPLBACKEND`, otherwise use Agg whenever the display is virtual, on all OSes; verify the starfield render test passes under Agg
- [ ] 6.3 Audit file I/O for `encoding="utf-8"` and OS-neutral paths (`os.path.join`/`pathlib`, no `/tmp` or `/home` literals outside Pi-only code); verify with `grep -rn "/home/\|/tmp\|/usr/share" --include=*.py` showing only Pi-only modules
- [ ] 6.4 Slim `web/dev_server.py` to call `main` with `--profile sim` (or remove it and update docs); verify `python -m web.dev_server` still serves http://localhost:8080

## 7. Integration and CI

- [ ] 7.1 Add `tests/test_smoke.py` (`slow`): run `python main.py --profile sim --duration 8` in a subprocess on a free port with `ASTROFLO_SNAPSHOT_DIR` in tmp; verify exit code 0, the web API answered during the run, and at least one snapshot and one solve were logged
- [ ] 7.2 Add `tests/test_hardware.py` with `pi_only`/`requires_camera` checks for the real finder camera, SV105 and TFT; verify they are skipped with reasons here and documented as `ASTROFLO_HW_TESTS=1 pytest -m "pi_only or requires_camera"` in `build/SETUP.md`
- [ ] 7.3 Add `.github/workflows/tests.yml` (ubuntu/macos/windows × Python 3.11, 3.13; `pytest -rs --timeout=120`) plus an ubuntu job with `requirements-solver.txt`; verify all jobs pass on a push to the branch
