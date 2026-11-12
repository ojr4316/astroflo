# runtime-platform Specification

## Purpose
Defines how astroflo chooses between real Raspberry Pi hardware and simulated hardware, and guarantees that the application starts and runs on Linux, macOS and Windows without any camera or physical screen attached.

## Requirements

### Requirement: Runtime profile selection
The system SHALL run in one of two profiles: `pi` (real hardware) or `sim` (simulated hardware). The profile SHALL be taken from, in order: the `--profile` command-line option, the `ASTROFLO_PROFILE` environment variable, then the saved settings, then automatic detection of a Raspberry Pi. The chosen profile SHALL be printed at startup.

#### Scenario: Default on a development machine
- **WHEN** astroflo starts on a non-Pi machine with no profile set
- **THEN** it runs in the `sim` profile and prints that it is simulating hardware

#### Scenario: Default on the Pi
- **WHEN** astroflo starts on the Raspberry Pi with no profile set
- **THEN** it runs in the `pi` profile and behaves as it does today

#### Scenario: Forced simulation on the Pi
- **WHEN** `ASTROFLO_PROFILE=sim` is set on the Pi
- **THEN** no camera, display or GPIO hardware is opened

#### Scenario: Invalid profile value
- **WHEN** the profile is set to an unknown value
- **THEN** startup fails with a message that lists the allowed values

### Requirement: Per-component backend override
The system SHALL let each hardware component (finder camera, imaging camera, solver, display, buttons) be set to a specific backend, overriding the profile default for that component only.

#### Scenario: Real solver with simulated camera
- **WHEN** the profile is `sim` and the solver backend is set to `tetra3`
- **THEN** simulated finder images are plate-solved by tetra3 while all other components stay simulated

#### Scenario: Backend unavailable on this platform
- **WHEN** a backend is requested that cannot run on the current OS or is not installed
- **THEN** startup fails with a message naming the backend and the reason, and does not fall back silently

### Requirement: Starts on Linux, macOS and Windows
In the `sim` profile the application SHALL start and run its main loop, web server and UI render loop on Linux, macOS and Windows with only the core dependencies installed, and with no camera, display, GPIO, `v4l2-ctl`, WSL or Cedar installed.

#### Scenario: Clean install on Windows
- **WHEN** core requirements are installed on Windows and `python main.py` is run
- **THEN** the app starts in `sim`, serves the web UI and keeps running until interrupted

#### Scenario: Headless Linux container
- **WHEN** the app is run on Linux with no `DISPLAY` and no `/dev/video*`
- **THEN** it starts without errors related to displays, fonts or cameras

### Requirement: Graceful handling of missing data files
When optional data files (planet/asteroid ephemerides, star catalog) are missing, the system SHALL keep running with the related features disabled, report which file is missing and how to obtain it, and SHALL NOT try to download it without being asked.

#### Scenario: No ephemeris file
- **WHEN** `data/de440s.bsp` is absent
- **THEN** startup continues, planet targets are not offered, and the log names the missing file

### Requirement: Platform-specific system actions
System actions that control the host (restart service, reboot, shut down) SHALL only run on Linux. On other platforms the web API SHALL reject them with a clear error and SHALL NOT run any command.

#### Scenario: Reboot requested on macOS
- **WHEN** a client calls the reboot action while astroflo runs on macOS
- **THEN** the API responds with an error stating the action is not supported on this platform

### Requirement: Clean shutdown
The application SHALL stop all of its threads and exit within 5 seconds when interrupted (Ctrl+C) or when a run-duration limit is given, on every supported platform.

#### Scenario: Timed headless run
- **WHEN** the app is started in `sim` with a run limit of 10 seconds
- **THEN** it exits on its own with status 0 after about 10 seconds
