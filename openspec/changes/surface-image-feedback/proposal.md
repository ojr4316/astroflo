# Proposal

## Why

The `feedback/` module already classifies each finder frame (lens cap on, over-exposed, blurred, field blocked), and `analyzer.py` stores the result — but nothing reads it. The user never sees these warnings, and the stored value is a raw class name (`CapOnRule`) with a 5 s expiry. Surfacing it turns existing work into actionable guidance at the eyepiece and on the web.

## What Changes

- Give each feedback rule a stable id, a short human-readable message, and a severity; report `OK` when no rule fires.
- Fix analyzer feedback state: initialise it at startup (today `get_feedback()` raises `AttributeError` before the first warning), keep the latest metrics alongside the result, and record when it was produced.
- Add a `feedback` object to `/api/state` (and so the `/ws/state` stream): current id, message, severity, age, and the metric values.
- Web UI: show a feedback banner on the Live tab, hidden when status is OK.
- On-device UI: show a one-line warning strip on every screen while a warning is active (alongside the existing status dot).
- Out of scope: new rules or tuning thresholds, `StarCount` metric (not wired in), feedback for the imaging camera.

## Capabilities

### New Capabilities
- `image-feedback`: Classification of finder frames into actionable warnings and how the current result is exposed (state API and web UI).

### Modified Capabilities
- `imaging-ui`: Adds an on-device warning strip for active image feedback.

## Impact

- `feedback/` (rule metadata), `analyzer.py` (state), `web/server.py` (snapshot), `web/static/{index.html,app.js,style.css}`, `hardware/renderer.py` + `hardware/ui.py` (strip).
- `/api/state` gains a `feedback` key — additive, no breaking change.
- Tests: `tests/test_web.py`, new `tests/test_image_feedback.py`, `tests/test_imaging_ui.py`.
