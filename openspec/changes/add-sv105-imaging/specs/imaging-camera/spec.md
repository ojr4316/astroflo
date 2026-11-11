# Spec Delta

## Purpose

Lets astroflo capture images of the night sky through an SVBONY SV105 imaging camera, either automatically while the selected target is in the field or manually on demand.

## ADDED Requirements

### Requirement: Imaging camera connection status
The system SHALL continuously report whether the SV105 imaging camera is connected and usable. The status SHALL update within 5 seconds of the camera being plugged in or unplugged, and the application SHALL keep running when the camera is absent or disconnected.

#### Scenario: Camera present at startup
- **WHEN** the application starts with the SV105 plugged in
- **THEN** the imaging camera status is reported as connected

#### Scenario: Camera absent at startup
- **WHEN** the application starts without the SV105 plugged in
- **THEN** the imaging camera status is reported as disconnected
- **AND** navigation, solving and all other features continue to work

#### Scenario: Camera unplugged during use
- **WHEN** the SV105 is unplugged while connected
- **THEN** the status changes to disconnected within 5 seconds
- **AND** any in-progress capture is abandoned without crashing the application

#### Scenario: Camera reconnected
- **WHEN** the SV105 is plugged back in after a disconnect
- **THEN** the status changes to connected within 5 seconds without restarting the application

### Requirement: Imaging camera is independent of the solving camera
The imaging camera SHALL operate independently of the plate-solving camera: imaging captures SHALL NOT change the solving camera's exposure or gain, and SHALL NOT feed frames into the plate solver.

#### Scenario: Imaging while solving
- **WHEN** automatic imaging is capturing frames
- **THEN** plate solving continues using only the solving camera's frames and settings

### Requirement: Automatic imaging mode toggle
The system SHALL provide an automatic imaging mode that the user can enable or disable at runtime. Automatic mode SHALL be disabled by default at startup.

#### Scenario: Default state
- **WHEN** the application starts
- **THEN** automatic imaging is disabled

#### Scenario: User enables auto mode
- **WHEN** the user enables automatic imaging
- **THEN** the system begins evaluating whether to capture on every subsequent cycle

### Requirement: Automatic capture only while target is in field
While automatic mode is enabled, the system SHALL capture frames only when the camera is connected, a target is selected, the latest plate solve is no older than 10 seconds, and the target lies within the imaging camera's field of view.

#### Scenario: Target in field
- **WHEN** auto mode is enabled, the camera is connected, and the most recent solve (under 10 s old) places the selected target inside the imaging field of view
- **THEN** the system captures and saves frames

#### Scenario: Target leaves field
- **WHEN** the target moves outside the imaging field of view
- **THEN** the system stops saving frames until the target is back in field

#### Scenario: No target selected
- **WHEN** auto mode is enabled but no target is selected
- **THEN** no frames are saved

#### Scenario: Stale solve
- **WHEN** the most recent successful plate solve is older than 10 seconds
- **THEN** no automatic frames are saved until a fresh solve confirms the target is in field

### Requirement: Automatic mode maximizes frame count
While the automatic capture conditions hold, the system SHALL capture frames back-to-back, starting the next exposure as soon as the previous frame is read, so that as many frames as possible are taken while the target is in field.

#### Scenario: Continuous capture
- **WHEN** the target remains in field for a period longer than several exposure times
- **THEN** the number of saved frames is approximately the in-field duration divided by the frame time (exposure plus readout), with no deliberate idle delay between frames

### Requirement: Automatic exposure and gain adjustment
In automatic mode the system SHALL adjust exposure and gain from the brightness of recent frames, aiming to keep the image neither under- nor over-exposed. It SHALL prefer longer exposure over higher gain, raise gain only when exposure is at its maximum, and keep both within the camera's supported ranges.

#### Scenario: Frame too dark
- **WHEN** a frame's brightness is below the target range and exposure is below its maximum
- **THEN** the next frames use a longer exposure with gain unchanged

#### Scenario: Frame too dark at max exposure
- **WHEN** a frame is below the target range and exposure is already at its maximum
- **THEN** gain is increased, up to the camera's maximum gain

#### Scenario: Frame overexposed
- **WHEN** a frame has more than the allowed fraction of saturated pixels or brightness above the target range
- **THEN** gain is reduced first; once gain is at its minimum, exposure is reduced

#### Scenario: Frame within range
- **WHEN** a frame's brightness is within the target range
- **THEN** exposure and gain are left unchanged

### Requirement: Manual capture
The system SHALL let the user capture a single frame on demand using the current exposure and gain, regardless of whether a target is selected, a solve exists, or automatic mode is enabled.

#### Scenario: Manual capture with camera connected
- **WHEN** the user triggers a manual capture and the camera is connected
- **THEN** exactly one frame is captured and saved as a manual capture

#### Scenario: Manual capture while auto is running
- **WHEN** the user triggers a manual capture while automatic imaging is capturing
- **THEN** one frame is saved as a manual capture and automatic imaging then resumes

#### Scenario: Manual capture with camera disconnected
- **WHEN** the user triggers a manual capture and the camera is disconnected
- **THEN** no file is written and the user is shown that the capture failed
