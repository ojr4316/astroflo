# Design

## Context

- The app runs as a set of threads started in `main.py` (camera capture, solver, UI draw, input, analyzer). Shared state lives in dataclasses on `ObservationContext`.
- `capture/camera.py` defines an abstract `Camera` used for the Pi plate-solving camera (`RPiCamera`) and a `FakeCamera` for dev machines; `is_pi()` selects between real and fake implementations.
- `TelescopeState.position` holds the latest solved (RA, Dec) of the telescope; `SolverState.last_solved` holds the solve time; `TargetState` holds the selected target.
- The SV105 is a UVC (USB Video Class) camera (Sony IMX307, 1920×1080, 2.9 µm pixels, ~5.6×3.2 mm sensor). On Linux it appears as `/dev/videoN` and is driven through V4L2; it exposes exposure and gain as UVC controls with a limited (sub-second) exposure range.
- Screens render 240×240 PIL images and every render helper in `hardware/renderer.py` ends with `_transform()` (rotate −90°) to match the physical display.

## Goals / Non-Goals

**Goals:**
- Run the imaging camera on its own thread, fully decoupled from the solving pipeline.
- Graceful handling of hot-plug: never crash the app because the SV105 is missing.
- Simple, testable auto exposure/gain logic and file naming (pure functions).

**Non-Goals:**
- Stacking, calibration frames (darks/flats), or FITS output.
- Long exposures beyond what the SV105 UVC driver supports.
- Persisting the Auto setting across restarts.
- Live preview of SV105 frames on the TFT (can be added later).

## Decisions

### 1. Driver via OpenCV `VideoCapture` (V4L2 backend)
Open the device with `cv2.VideoCapture(index, cv2.CAP_V4L2)`, request 1920×1080 and an uncompressed format (YUYV) when available, disable auto-exposure (`CAP_PROP_AUTO_EXPOSURE` → manual) and set `CAP_PROP_EXPOSURE` / `CAP_PROP_GAIN`. Locate the device by scanning `/sys/class/video4linux/*/name` for the SV105 name (fallback: configurable index) so the Pi camera's video nodes are never opened by mistake.
- *Alternative:* SVBONY SDK — the SV105 is UVC-only and not supported by the SV SDK; rejected.
- *Alternative:* shelling out to `v4l2-ctl` for every control — kept only as fallback if OpenCV control properties are ignored by the driver (record ranges via `v4l2-ctl --list-ctrls` during task 2.1).
- Read the supported exposure/gain min/max at connect time and expose them as `limits` so auto logic clamps to the real ranges. Flush 1–2 frames after changing controls since UVC applies settings with a lag.

### 2. Class layout
- `capture/imaging_camera.py`: abstract `ImagingCamera` with `connect() -> bool`, `is_connected() -> bool`, `configure(exposure_us, gain)`, `capture() -> np.ndarray | None`, `limits`, `close()`. Separate from the existing `Camera` ABC because that class owns a solver queue and a `capturer` loop that don't apply here.
- `capture/sv105_camera.py`: `SV105Camera(ImagingCamera)` (real driver).
- `capture/fake_imaging_camera.py`: returns frames from `test_data/` with a simulated connect/disconnect toggle for dev testing.
- `capture/auto_exposure.py`: pure function `next_settings(frame, exposure, gain, limits) -> (exposure, gain)`.
- `capture/v4l2_util.py`: device lookup by sysfs name and `v4l2-ctl` parsing (shared with the probe tool).
- `capture/image_store.py`: pure-ish `ImageStore(base_dir)` with `sanitize(name)`, `path_for(target_or_none, now)` and `save(frame, target_or_none) -> path`.
- `capture/imaging.py`: `ImagingController` with a `run()` loop, owned by `main.py` on its own thread.

### 3. Shared state
Add `ImagingState` dataclass to `observation_context.py`: `connected`, `auto_enabled` (default False), `exposure_us`, `gain`, `target_in_field`, `frames_saved`, `last_result` (+ timestamp, for the "Saved"/"Failed" toast), and `manual_requested` (a `threading.Event`). UI only reads state and sets `auto_enabled` / the manual event; the controller thread is the only code that touches the device, avoiding concurrent V4L2 access.

### 4. Controller loop
```
loop:
  if not connected: try connect every 2 s (hot-plug); update state.connected; continue
  if manual_requested: capture → save to saves/manual → set last_result; clear event; continue
  if auto_enabled and target_in_field():
      frame = capture(); if None → mark disconnected; continue
      save to saves/<target>; frames_saved += 1
      apply next_settings(frame) if changed
      continue                       # no sleep: back-to-back frames
  else: sleep 0.1 s and poll connection (cheap read/ioctl) every ~2 s
```
A failed `read()` (returns False) or exception marks the camera disconnected and releases it, satisfying the 5 s detection requirement via the 2 s retry. Saving runs inline initially; if PNG encoding at 1080p measurably limits frame rate on the Pi, move saves to a small writer queue/thread (bounded, drop-oldest never — block instead to avoid losing frames).

### 5. Target-in-field test
`target_in_field = target_state.has_target() and telescope_state.position is not None and time.time() - solver_state.last_solved <= 10 and haversine_dist(pos, target) <= imaging_radius`.
`imaging_radius` = half the diagonal FOV computed from sensor size and `TelescopeOptics.focal_length` (IMX307 5.6×3.2 mm at 1200 mm ≈ 0.31° diagonal → radius ≈ 0.15°), with a small configurable margin factor (default 1.0). Uses the existing `utils.haversine_dist` (returns radians → convert). `TelescopeState.position` already incorporates the camera→telescope alignment, so it represents the scope's optical axis where the SV105 sits.

### 6. Auto exposure/gain algorithm
Targets range from the Moon (fills the 0.31° field at 1200 mm, very bright) to faint clusters in light-polluted skies (background-limited) — roughly four decades of exposure×gain. Measure on a 4× downsampled grayscale frame: median brightness `m` (0–255; the lunar surface or the sky background) and saturated fraction `s` (pixels ≥ 250).
- Target band: `m` in [40, 110], `s` ≤ 0.5% (a few saturated stars stay under this; a lunar limb blown out does not).
- Too dark: scale exposure by `clamp(70 / m, 1.25, 4)`; once exposure is at max, raise gain by 10% of the range (25% when `m` is under half the target).
- Too bright / saturated: lower gain first by 10% (25% when far off); once gain is at min, scale exposure by `clamp(70 / m, 0.25, 0.8)`; with `s` > 20% the median is meaningless, so use the full 0.25 step.
- Within band: unchanged (band width gives hysteresis).
Rationale: longer exposure beats gain for SNR; large multiplicative steps cover Moon→cluster in ~10 frames. Constants live at the top of `capture/auto_exposure.py` for field tuning.
- *Known limitation:* small bright targets on a dark sky (e.g. planets) can be overexposed, since the median is the sky and the saturated area is below 0.5%. Not a goal of this change.
- *Alternative:* the existing `Adjuster` (solve success/fail streaks) — wrong signal for imaging; rejected.

### 6b. Measuring real limits on the Pi
UVC cameras commonly advertise exposures they don't deliver, and long exposures are often capped by the frame interval. `tools/sv105_probe.py` sweeps exposure (geometric ×2 steps at min gain) and gain (11 steps at a mid exposure), recording mean, noise, saturation and frame interval per step. The effective maximum is the last step where signal (or frame time / noise for gain) still grew ≥ 8%. Results go to `data/sv105_limits.json`, which `SV105Camera` loads to override reported ranges, along with resolution/format and supported frame rates. The driver enables `exposure_dynamic_framerate` when present and picks the highest frame rate whose interval fits the exposure, so long exposures aren't silently truncated.

### 7. Storage
`saves/` at `BASE_DIR`. Directory `manual` for manual captures, else `sanitize(target_state.name)`. File name `datetime.now().strftime("%Y-%m-%d_%H-%M-%S-") + f"{ms:03d}"` + `.png`, with `_1`, `_2`… suffix on collision. PNG for lossless output; frames converted to BGR for `cv2.imwrite`. A target literally named "manual" would share the manual folder — accepted (unlikely; can prefix later).

### 8. UI
- **Status dot:** add `draw_status_dot(img)` in `renderer.py`, called by every render helper just before `_transform()`. It reads connection status via a module-level provider (`renderer.status_provider = lambda: ctx.imaging_state.connected`) set by `UIManager` at startup — avoids threading state through every screen signature. 8 px circle at a fixed corner (top-right of the logical canvas) with a dark outline for contrast.
- **Imaging screen:** new `ScreenState.IMAGING`, `hardware/screens/imaging.py`, added to `ScreenFactory` and as a fifth main-menu option. Layout: back button + two buttons ("Auto: On/Off", "Capture") using `render_menu`-style buttons, plus status text lines (Exp, Gain, In field yes/no, Saved N, last result toast for 2 s). Controls follow existing conventions: L/R move selection, A activates (toggle Auto / request capture), B goes back to the main menu.

## Risks / Trade-offs

- [SV105 UVC exposure range is short (fraction of a second)] → Auto logic clamps to reported limits and compensates with gain; document real ranges once measured.
- [OpenCV may silently ignore exposure/gain properties on some V4L2 drivers] → verify by reading back properties after setting; fall back to `v4l2-ctl` subprocess if needed.
- [USB bandwidth / CPU on Pi with two cameras + PNG encoding] → measure fps on the Pi; move saving to a writer thread or switch to lower PNG compression level if frame rate suffers.
- [Wrong /dev/video node (Pi camera also exposes video nodes)] → select by device name from sysfs, not by index.
- [Disk fills during long auto sessions] → out of scope now; log a warning and stop auto mode if `cv2.imwrite` fails.
- [Imaging FOV margin: stale or imprecise solves may save frames slightly off target] → 10 s staleness limit and configurable margin factor.

## Migration Plan

Additive change; no data migration. On the Pi, ensure the user running astroflo is in the `video` group. Rollback: remove the imaging thread start in `main.py`.

## Open Questions

- Exact SV105 exposure/gain ranges on the Pi: measured by `tools/sv105_probe.py`; only affects `data/sv105_limits.json`.
- Whether to also save a small JSON sidecar with exposure/gain/RA/Dec per frame (easy follow-up).
