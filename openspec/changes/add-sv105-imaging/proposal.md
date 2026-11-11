# Proposal

## Why

Astroflo currently only uses the Pi camera for plate solving and navigation; there is no way to capture science/keeper images through the telescope. Adding support for an SVBONY SV105 imaging camera lets the device photograph the selected target, either hands-free while the target is in the field or on demand.

## What Changes

- Add an SV105 imaging camera driver, independent from the existing plate-solving camera, with connection detection and hot-plug tolerance (disconnect/reconnect without crashing the app).
- Add an **automatic imaging mode**: when enabled and the selected target is within the imaging camera's field of view (based on the latest plate solve), continuously capture as many frames as possible, adapting exposure and gain from frame brightness.
- Add a **manual imaging mode**: a button press captures a single frame using the current exposure/gain, regardless of target or pointing.
- Save images under `saves/<target-name>/` (auto mode) or `saves/manual/` (manual captures), with timestamp file names. `saves/` is git-ignored.
- UI:
  - A red/green dot indicating imaging camera connection, visible on every screen.
  - A new "Imaging" screen reachable from the main menu, with an Auto on/off setting and a manual Capture button, plus status (mode, exposure, gain, frames saved this session).
- Provide a fake imaging camera for non-Pi development, mirroring the existing fake camera/solver pattern.

## Capabilities

### New Capabilities
- `imaging-camera`: Connecting to the SV105, reporting connection status, and capturing frames in automatic (target-in-field, adaptive exposure/gain) and manual modes.
- `image-storage`: Where and how captured images are written (directory per target or `manual`, timestamp file names, collision handling).
- `imaging-ui`: On-device UI for imaging: connection indicator, auto-mode setting, and manual capture button.

### Modified Capabilities
<!-- None: no existing specs in openspec/specs/. -->

## Impact

- New code: `capture/imaging_camera.py` (interface), `capture/sv105_camera.py` (driver), `capture/fake_imaging_camera.py`, `capture/auto_exposure.py`, `capture/imaging.py` (controller loop), `capture/image_store.py`, `hardware/screens/imaging.py`, plus unit tests under `tests/`.
- Modified: `observation_context.py` (new `ImagingState`), `main.py` (build + start imaging thread), `hardware/state.py` (`ScreenState.IMAGING`), `hardware/screen_factory.py`, `hardware/screens/main_menu.py` (new menu entry), `hardware/renderer.py` (status dot overlay), `.gitignore` (`saves/`).
- Dependencies: uses `opencv-python` (already present) via V4L2/UVC; no new Python packages expected. Optional `v4l2-ctl` (v4l-utils) on the Pi for manual-exposure controls if OpenCV properties prove insufficient.
- Hardware: SV105 attached by USB to the Pi alongside the existing Pi camera.
