# Spec Delta

## Purpose

Provides stand-ins for the finder camera, imaging camera, TFT display and buttons, driven by recorded test images and scripted input, so the whole app can be developed and tested without physical hardware.

## ADDED Requirements

### Requirement: Simulated finder camera replays test images
The simulated finder camera SHALL produce frames from image files in a configurable folder (default `test_data/`), in file-name order, looping back to the first image after the last. Frames SHALL have the same array shape and color order as real finder camera frames.

#### Scenario: Folder of images
- **WHEN** the simulated finder camera is pointed at a folder with three JPEG images
- **THEN** successive captures return image 1, 2, 3, 1, ... as RGB arrays

#### Scenario: Single image file
- **WHEN** the source is set to a single image path
- **THEN** every capture returns that image

#### Scenario: Empty or missing folder
- **WHEN** the source folder contains no readable images
- **THEN** startup reports the folder and the camera produces random-noise frames instead of crashing

### Requirement: Simulated finder camera timing
The simulated finder camera SHALL wait for the configured exposure time per frame by default, and SHALL allow that wait to be disabled so tests can run fast.

#### Scenario: Fast mode in tests
- **WHEN** exposure simulation is disabled
- **THEN** a capture returns without sleeping for the exposure time

### Requirement: Simulated imaging camera from test images
The simulated imaging camera SHALL optionally produce frames from a folder of test images, with brightness scaled by exposure and gain the same way as its synthetic frames, and SHALL still support simulated unplug and reconnect.

#### Scenario: Exposure changes brightness
- **WHEN** the same test image is captured at 0.1 s and then at 0.2 s exposure with equal gain
- **THEN** the mean pixel value of the second frame is higher, up to saturation

#### Scenario: Simulated unplug
- **WHEN** the simulated imaging camera is marked as unplugged
- **THEN** it reports disconnected and returns no frames until it is marked present again

### Requirement: Headless virtual display
In the `sim` profile the UI SHALL render screens continuously into an in-memory virtual display at the same 240×240 size and brightness handling as the TFT, and SHALL NOT open any OS window.

#### Scenario: Latest frame available
- **WHEN** the UI loop has been running in `sim` for one second
- **THEN** the latest rendered 240×240 frame is available to the web UI and to tests

#### Scenario: Snapshot to disk
- **WHEN** display snapshots are enabled with an output folder
- **THEN** rendered frames are written there as PNG files

#### Scenario: Display disabled
- **WHEN** the display is turned off from settings
- **THEN** the virtual display stops rendering, as the TFT does

### Requirement: Simulated button input
The system SHALL accept simulated presses, releases and holds of the seven TFT buttons (A, B, L, R, U, D, C) through the same input handling as the physical buttons, from code, from a scripted sequence, and from the web API in the `sim` profile.

#### Scenario: Navigate menu from a script
- **WHEN** a script moves down one item (the L button on the rotated screen) and then presses A on the main menu
- **THEN** the UI changes to the screen of the second menu item, exactly as with physical buttons

#### Scenario: Web input in sim
- **WHEN** a client posts a press of button A to the simulated input endpoint while in `sim`
- **THEN** the current screen handles an A press

#### Scenario: Web input on real hardware
- **WHEN** the same endpoint is called in the `pi` profile with real buttons
- **THEN** the request is rejected

### Requirement: Simulated solver results
The simulated solver SHALL return a configurable fixed sky position by default, and SHALL be replaceable by the real tetra3 solver so recorded star-field images are plate-solved on any OS.

#### Scenario: Tetra3 on a recorded image
- **WHEN** tetra3 is installed and the solver backend is `tetra3` with the simulated camera replaying a recorded star field
- **THEN** the solver reports a position that matches the field recorded in the image
