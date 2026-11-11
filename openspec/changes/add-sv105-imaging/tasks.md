# Tasks

## 1. State and storage

- [x] 1.1 Add `ImagingState` dataclass to `observation_context.py` (connected, auto_enabled=False, exposure_us, gain, target_in_field, frames_saved, last_result + timestamp, manual_requested Event) and attach it to `ObservationContext`; verify `ObservationContext().imaging_state.auto_enabled is False`
- [x] 1.2 Implement `capture/image_store.py` (`sanitize`, `path_for`, `save`) writing PNGs to `saves/<target>/` or `saves/manual/` with `YYYY-MM-DD_HH-MM-SS-mmm.png` names and `_N` collision suffix; verify with `tests/test_image_store.py` (sanitization incl. "NGC 224 / Andromeda" and empty name, manual dir, timestamp format, collision, dir creation using a tmp dir)
- [x] 1.3 Add `saves/` to `.gitignore`; verify `git status` shows no files after saving a test image

## 2. Imaging camera drivers

- [x] 2.1 Create `capture/imaging_camera.py` ABC (`connect`, `is_connected`, `configure`, `capture`, `limits`, `close`); verify module imports on a non-Pi machine
- [x] 2.2 Implement `capture/sv105_camera.py` + `capture/v4l2_util.py` using `cv2.VideoCapture(..., cv2.CAP_V4L2)`, locating the device by sysfs name, setting manual exposure + gain via `v4l2-ctl` (OpenCV fallback), enabling dynamic frame rate, loading measured limits from `data/sv105_limits.json`, and treating failed reads as disconnect; verify v4l2 output parsing with `tests/test_imaging_cameras.py`
- [x] 2.3 Implement `capture/fake_imaging_camera.py` simulating scene brightness vs exposure/gain with a toggleable connected flag; verify with a unit test that capture returns None while "disconnected"
- [x] 2.4 Implement `tools/sv105_probe.py` (exposure + gain sweeps, effective-limit detection, writes `data/sv105_limits.json`, `--dry-run`); verify `python3 tools/sv105_probe.py --help` runs on a dev machine

## 3. Auto exposure and controller

- [x] 3.1 Implement `capture/auto_exposure.py` `next_settings(frame, exposure, gain, limits)` per design §6; verify with `tests/test_auto_exposure.py` covering dark → exposure up, dark at max exposure → gain up, saturated → gain down then exposure down, in-band → unchanged, clamping, and convergence for a Moon-bright and a cluster-dim simulated scene
- [x] 3.2 Implement imaging field radius from sensor size + focal length and a `target_in_field(ctx)` helper (target set, solve ≤ 10 s old, haversine distance ≤ radius); verify with unit tests for in-field, out-of-field, no target, stale solve
- [x] 3.3 Implement `capture/imaging.py` `ImagingController.run()` loop per design §4 (reconnect every 2 s, manual request handling, back-to-back auto captures, settings updates, frames_saved/last_result updates); verify with `tests/test_imaging_controller.py` driving the fake camera
- [x] 3.4 Wire into `main.py`: build `SV105Camera` on Pi / `FakeImagingCamera` otherwise and start the controller thread (daemon); verify app starts on a dev machine with no SV105 and solving/UI still run

## 4. UI

- [x] 4.1 Add `draw_status_dot` + `status_provider` to `hardware/renderer.py`, drawn in `_transform()` so every screen gets it, and set the provider in `UIManager`; verify with `tests/test_imaging_ui.py` that the corner pixel is green/red
- [x] 4.2 Add `ScreenState.IMAGING`, `hardware/screens/imaging.py` (Auto toggle, Capture button, status lines, 2 s Saved/Failed toast, B → main menu), register in `ScreenFactory`; verify with unit tests that toggling flips `auto_enabled` and Capture sets `manual_requested`
- [x] 4.3 Add "Imaging" to the main menu options and route it to `ScreenState.IMAGING`; verify `MainMenu.select` on the Imaging entry switches to `ScreenState.IMAGING`

## 5. Pi: measure camera limits

- [ ] 5.1 Install tools: `sudo apt install v4l-utils`, add user to `video` group; verify `v4l2-ctl --list-devices` lists the SV105
- [ ] 5.2 Dry run in daylight-free conditions (scope capped but not light-tight, or dark room with faint light): `python3 tools/sv105_probe.py --dry-run`; verify the exposure table shows no `SAT` rows at long exposures (dim the scene and repeat if it does)
- [ ] 5.3 Run `python3 tools/sv105_probe.py` to write `data/sv105_limits.json`; verify the reported effective max exposure/gain are plausible (frame time grows with exposure up to the max; noise grows with gain) and record them in design.md
- [ ] 5.4 If the measured max exposure is well below the reported max, repeat with `--width 1280 --height 720` and/or `--fourcc MJPG` to see if a lower-bandwidth mode allows longer exposures; keep the best mode in the limits file

## 6. Pi: integration on sky

- [ ] 6.1 Unplug/replug the SV105 while astroflo runs and confirm the dot changes red/green within 5 s with no crash
- [ ] 6.2 Moon: select the Moon, enable Auto, center it; confirm frames accumulate in `saves/Moon/`, gain drops to min, exposure settles with no blown-out surface
- [ ] 6.3 Dim cluster under light pollution (e.g. M13 / M36): enable Auto; confirm exposure climbs to the measured max then gain rises, background median sits in band, and frames stop when slewed away
- [ ] 6.4 Press Capture on the Imaging screen and confirm exactly one file in `saves/manual/` and a "Saved" toast
- [ ] 6.5 Tune constants in `capture/auto_exposure.py` from 6.2/6.3 results if needed and re-run `pytest tests`

## Workflow follow-up

- Archive the change (`openspec archive add-sv105-imaging`) after implementation is verified on hardware.
