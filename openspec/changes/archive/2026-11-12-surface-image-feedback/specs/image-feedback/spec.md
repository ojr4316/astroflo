# Spec Delta

## Purpose

Tells the user when finder frames are unusable (cap on, over-exposed, out of focus, field blocked) and why, so they can correct it.

## ADDED Requirements

### Requirement: Frame classification with readable messages
Each analysed finder frame SHALL be classified into at most one feedback condition, choosing the highest-priority matching condition. Each condition SHALL have a stable id, a short human-readable message, and a severity (`warning` or `error`). When no condition matches, the result SHALL be `OK`.

#### Scenario: Lens cap on
- **WHEN** a frame with near-zero brightness is analysed
- **THEN** the result id is `cap_on` with message "Lens cap on?" and severity `error`

#### Scenario: Multiple conditions match
- **WHEN** a frame matches both the blur and field-blocked conditions
- **THEN** only the higher-priority condition (blur) is reported

#### Scenario: Good frame
- **WHEN** a frame matches no condition
- **THEN** the result id is `ok` and no warning is shown

### Requirement: Feedback state is always readable
The current feedback SHALL be readable at any time, including before any frame has been analysed. A warning SHALL remain current until a later frame clears it or it is older than 5 seconds.

#### Scenario: Before first frame
- **WHEN** feedback is read before any frame is analysed
- **THEN** the result is `ok` and no error is raised

#### Scenario: Warning clears
- **WHEN** a warning was reported and the next analysed frame matches no condition
- **THEN** the current feedback becomes `ok`

#### Scenario: Warning expires
- **WHEN** a warning is more than 5 seconds old and no newer frame has been analysed
- **THEN** the current feedback is `ok`

### Requirement: Feedback in the state API
The state snapshot (`GET /api/state` and `/ws/state`) SHALL include a `feedback` object with `id`, `message`, `severity` (null when OK), `age_s`, and the latest metric values by name.

#### Scenario: Active warning
- **WHEN** the latest frame was classified as over-exposed
- **THEN** `feedback.id` is `over_exposed` and `feedback.metrics` includes the saturated-pixel fraction

#### Scenario: No frames yet
- **WHEN** the state is requested before any frame is analysed
- **THEN** `feedback.id` is `ok` and `feedback.metrics` is empty

### Requirement: Web feedback banner
The web Live tab SHALL show a banner with the feedback message while a warning is active, styled by severity, and SHALL hide it when feedback is OK.

#### Scenario: Warning shown
- **WHEN** the state stream reports `feedback.id` `blurred`
- **THEN** the Live tab shows the blur message in a warning-styled banner

#### Scenario: Warning cleared
- **WHEN** a later state update reports `feedback.id` `ok`
- **THEN** the banner is hidden
