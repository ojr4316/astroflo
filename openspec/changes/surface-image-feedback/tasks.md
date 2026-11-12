# Tasks

## 1. Feedback classification

- [ ] 1.1 Add `id`, `message`, `severity` to `ClassificationRule` and each rule (cap_on/"Lens cap on?"/error, over_exposed/"Over-exposed — lower exposure or gain"/warning, blurred/"Out of focus"/warning, field_blocked/"Field blocked?"/warning); set explicit priorities per design; verify by `pytest tests/test_image_feedback.py`
- [ ] 1.2 Add `FeedbackResult` + `OK` constant; make `classify()` return it with metrics keyed by `Metric.value`; add `tests/test_image_feedback.py` with synthetic frames (black → cap_on, saturated → over_exposed, uniform grey → blurred, star field → ok, blur+blocked → blurred) and verify they pass

## 2. Analyzer state

- [ ] 2.1 Initialise feedback state in `Analyzer.__init__`; store latest `FeedbackResult` + timestamp under a lock on every frame; `get_feedback()` returns `OK` when unset or older than 5 s; update the one caller in `process()`; add tests for before-first-frame, clear-on-ok and expiry (monkeypatched time) and verify they pass

## 3. State API and web UI

- [ ] 3.1 Add `feedback` (`id`, `message`, `severity`, `age_s`, `metrics`) to `snapshot()` in `web/server.py`; extend `tests/test_web.py` for the no-frames and active-warning cases and verify `pytest tests/test_web.py` passes
- [ ] 3.2 Add a hidden banner to the Live tab in `index.html`, toggle/style it from `app.js` state handler with severity classes in `style.css`; verify with `web/dev_server.py` that the banner appears for a forced warning and hides on ok

## 4. On-device strip

- [ ] 4.1 Add `feedback_provider` hook and `draw_feedback_strip()` to `hardware/renderer.py`, called from `_transform()`, failing silently; wire it in `hardware/ui.py` to `analyzer.get_feedback`; add tests in `tests/test_imaging_ui.py` that the strip pixels are drawn for a warning, absent for ok, and absent when the provider raises, and verify they pass

## 5. Integration

- [ ] 5.1 Run full `pytest` and verify all tests pass
