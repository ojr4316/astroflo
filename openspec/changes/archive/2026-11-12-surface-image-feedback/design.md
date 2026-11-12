# Design

## Context

- `ImagingFeedback.classify()` returns `(rule.__class__.__name__, metrics)`; metrics are keyed by `Metric` enum members.
- `Analyzer.process()` runs in its own thread on finder frames from the solver queue, calling `add_feedback()` only for non-`NONE` results. `feedback_text` is never initialised, so `get_feedback()` crashes until a warning fires. Nothing calls `get_feedback()`.
- Web state is built in `web/server.py:snapshot()` and pushed every 0.5 s; the device draws the status dot in `renderer._transform()` via a module-level `status_provider` set by `UIManager`.
- `OverExposedRule` and `CapOnRule` share priority 100; order between them depends on sort stability.

## Goals / Non-Goals

**Goals:** expose existing classification with readable text; no behaviour change to rule thresholds.

**Non-Goals:** rule tuning, `StarCount`, aspect-correct resizing in `classify()` (noted as risk), imaging-camera feedback.

## Decisions

- **Rule metadata on the rule class** (`id`, `message`, `severity` class attributes on `ClassificationRule` subclasses). Keeps one place to add a rule. Alternative: a lookup table in `analyzer.py` — drifts when rules are added.
- **`classify()` returns a small `FeedbackResult` dataclass** (`id`, `message`, `severity`, `metrics`) with metrics keyed by `Metric.value` strings, so they serialise to JSON directly. `ok` is a module constant.
- **Analyzer stores the latest result + timestamp under a lock**, set on every frame (including `ok`) so good frames clear warnings immediately; `get_feedback()` returns `ok` if older than 5 s. Replaces `add/clear_feedback` text API.
- **Explicit priorities:** cap_on 110, over_exposed 100, blurred 10, field_blocked 5 — removes the tie.
- **Device strip via a second renderer hook** (`feedback_provider`, mirroring `status_provider`) drawn in `_transform()`. Alternative: per-screen drawing — would need edits to every screen.
- **Web banner** is a single element at the top of the Live tab, toggled in the existing state handler; severity maps to CSS classes.

## Risks / Trade-offs

- [Thresholds were tuned on normalised, force-resized 1000×1000 images and may misfire on real frames] → keep behaviour unchanged; banner/strip just reveal it. Tuning is a follow-up.
- [Strip covers bottom 18 px, overlapping `render_image_with_caption` bottom captions] → draw strip only while a warning is active; accept temporary overlap.
- [Analyzer thread and web/UI threads read concurrently] → lock around result swap.
