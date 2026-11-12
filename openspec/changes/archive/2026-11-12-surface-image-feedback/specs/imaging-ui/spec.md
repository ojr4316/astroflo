# Spec Delta

## ADDED Requirements

### Requirement: On-device feedback strip
While an image-feedback warning is active, every screen SHALL show a one-line strip with the feedback message along the bottom edge, coloured by severity. The strip SHALL disappear on a subsequent redraw once feedback is OK.

#### Scenario: Warning on any screen
- **WHEN** feedback reports "Lens cap on?" while the user is on the Navigation screen
- **THEN** the strip shows "Lens cap on?" in error colour without user input

#### Scenario: Warning cleared
- **WHEN** feedback returns to OK
- **THEN** the strip is no longer drawn on the next redraw

#### Scenario: Feedback unavailable
- **WHEN** reading feedback raises an error
- **THEN** the screen renders normally without a strip
