# Tasks

## 1. State and storage

- [ ] 1.1 Add `ImagingState` dataclass to `observation_context.py` (connected, auto_enabled=False, exposure_us, gain, target_in_field, frames_saved, last_result + timestamp, manual_requested Event) and attach it to `ObservationContext`; verify `ObservationContext().imaging_state.auto_enabled is False`
- [ ] 1.2 Implement `capture/image_store.py` (`sanitize`, `path_for`, `save`) writing PNGs to `saves/<target>/` or `saves/manual/` with `YYYY-MM-DD_HH-MM-SS-mmm.png` names and `_N` collision suffix; verify with `tests/test_image_store.py` (sanitization incl. "NGC 224 / Andromeda" and empty name, manual dir, timestamp format, collision, dir creation using a tmp dir)
- [ ] 1.3 Add `saves/` to `.gitignore`; verify `git status` shows no files after saving a test image

## 2. Imaging camera drivers

- [ ] 2.1 Create `capture/imaging_camera.py` ABC (`connect`, `is_connected`, `configure`, `capture`, `limits`, `close`); verify module imports on a non-Pi machine
- [ ] 2.2 Implement `capture/sv105_camera.py` using `cv2.VideoCapture(..., cv2.CAP_V4L2)`, locating the device by sysfs name, setting manual exposure + gain, reading back limits, and treating failed reads as disconnect; verify on the Pi that connect/capture/configure work and record measured exposure/gain ranges in design.md
- [ ] 2.3 Implement `capture/fake_imaging_camera.py` serving `test_data/` frames with a toggleable connected flag; verify with a unit test that capture returns None while "disconnected"

## 3. Auto exposure and controller

- [ ] 3.1 Implement `capture/auto_exposure.py` `next_settings(frame, exposure, gain, limits)` per design §6; verify with `tests/test_auto_exposure.py` covering dark → exposure up, dark at max exposure → gain up, saturated → gain down then exposure down, in-band → unchanged, clamping to limits
- [ ] 3.2 Implement imaging field radius from sensor size + focal length and a `target_in_field(ctx)` helper (target set, solve ≤ 10 s old, haversine distance ≤ radius); verify with unit tests for in-field, out-of-field, no target, stale solve
- [ ] 3.3 Implement `capture/imaging.py` `ImagingController.run()` loop per design §4 (reconnect every 2 s, manual request handling, back-to-back auto captures, settings updates, frames_saved/last_result updates); verify with a test driving the fake camera: auto saves only while in field, manual saves one file to `saves/manual`, disconnect flips `connected` within 5 s
- [ ] 3.4 Wire into `main.py`: build `SV105Camera` on Pi / `FakeImagingCamera` otherwise and start the controller thread; verify app starts on a dev machine with no SV105 and solving/UI still run

## 4. UI

- [ ] 4.1 Add `draw_status_dot` + `status_provider` to `hardware/renderer.py`, call it in every render helper before `_transform()`, and set the provider in `UIManager`; verify by rendering a screen with connected True/False and checking the corner pixel is green/red
- [ ] 4.2 Add `ScreenState.IMAGING`, `hardware/screens/imaging.py` (Auto toggle, Capture button, status lines, 2 s Saved/Failed toast, B → main menu), register in `ScreenFactory`; verify by unit-calling select handlers: toggling flips `auto_enabled`, Capture sets `manual_requested`
- [ ] 4.3 Add "Imaging" to the main menu options and route it to `ScreenState.IMAGING`; verify navigation on the device (or by calling `MainMenu.select` with index 4)

## 5. Integration

- [ ] 5.1 On the Pi with SV105: unplug/replug and confirm the dot changes red/green within 5 s with no crash
- [ ] 5.2 On the Pi: select a target, enable Auto, slew onto target and confirm frames accumulate in `saves/<target>/` with timestamp names, stop when slewed away, and exposure/gain adapt; press Capture and confirm one file in `saves/manual/`
- [ ] 5.3 Run `pytest` and confirm all new tests pass

## Workflow follow-up

- Archive the change (`openspec archive add-sv105-imaging`) after implementation is verified on hardware.
