# imaging-ui Specification

## Purpose
Gives the user on-device visibility and control of the imaging camera: connection status at a glance, an automatic-mode setting, and a manual capture button.

## Requirements

### Requirement: Connection indicator on every screen
Every screen SHALL show a small status dot in a fixed corner: green when the imaging camera is connected, red when it is disconnected. The dot SHALL reflect the current connection status on each redraw.

#### Scenario: Connected
- **WHEN** the imaging camera is connected
- **THEN** a green dot is shown on whichever screen is displayed

#### Scenario: Disconnected
- **WHEN** the imaging camera is disconnected
- **THEN** a red dot is shown on whichever screen is displayed

#### Scenario: Status change while viewing a screen
- **WHEN** the camera is unplugged while the user is on any screen
- **THEN** the dot turns from green to red on a subsequent redraw without user input

### Requirement: Imaging screen reachable from main menu
The main menu SHALL include an "Imaging" entry that opens an Imaging screen. The back button SHALL return from the Imaging screen to the main menu.

#### Scenario: Open imaging screen
- **WHEN** the user selects "Imaging" in the main menu
- **THEN** the Imaging screen is displayed

#### Scenario: Leave imaging screen
- **WHEN** the user presses back on the Imaging screen
- **THEN** the main menu is displayed and automatic mode keeps its current setting

### Requirement: Auto mode setting
The Imaging screen SHALL show an "Auto" setting with its current value (On/Off) that the user can toggle.

#### Scenario: Toggle auto on
- **WHEN** the user toggles Auto while it is Off
- **THEN** the setting shows On and automatic imaging is enabled

#### Scenario: Toggle auto off
- **WHEN** the user toggles Auto while it is On
- **THEN** the setting shows Off and automatic imaging stops after the current frame

### Requirement: Manual capture button
The Imaging screen SHALL provide a "Capture" button that triggers one manual capture, and SHALL briefly show the result (saved or failed).

#### Scenario: Capture succeeds
- **WHEN** the user presses Capture with the camera connected
- **THEN** one manual frame is saved and the screen shows a "Saved" confirmation

#### Scenario: Capture fails
- **WHEN** the user presses Capture with the camera disconnected
- **THEN** the screen shows a failure message and no file is written

### Requirement: Imaging status display
The Imaging screen SHALL display the current exposure, gain, whether the target is in field, and the number of frames saved this session.

#### Scenario: Auto imaging running
- **WHEN** automatic imaging is saving frames of the target
- **THEN** the screen shows the target as in field and the saved-frame count increases as frames are written

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
