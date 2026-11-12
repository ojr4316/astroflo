# test-suite Specification

## Purpose
Defines how the automated test suite is organized so it runs on every supported OS without hardware, skips only what truly cannot run there, and still covers every feature that can be exercised in simulation.

## Requirements

### Requirement: Tests run without hardware by default
The test suite SHALL assume no camera, display, GPIO or Pi is attached unless one is detected or explicitly enabled, and SHALL pass on Linux, macOS and Windows with only core and test dependencies installed.

#### Scenario: Plain pytest on a laptop
- **WHEN** `pytest` is run on macOS with no camera
- **THEN** all tests pass or are skipped, and none fails because hardware or a Linux tool is missing

### Requirement: Conditional skips by requirement
Tests that need a specific OS, hardware, external tool, optional package or data file SHALL be marked with the requirement they need and SHALL be skipped, with a reason naming that requirement, when it is not met. Tests SHALL NOT be skipped for any other reason.

#### Scenario: Linux-only test on Windows
- **WHEN** a test marked as needing Linux runs on Windows
- **THEN** it is reported as skipped with a reason such as "requires Linux"

#### Scenario: Camera test with no camera
- **WHEN** a test marked as needing a real camera runs and no camera is detected
- **THEN** it is skipped with a reason naming the camera

#### Scenario: Opt in to hardware tests
- **WHEN** hardware tests are enabled explicitly on the Pi with the cameras attached
- **THEN** camera and display tests run instead of being skipped

### Requirement: Platform-independent logic is tested everywhere
Logic that does not touch hardware SHALL have tests that run unskipped on every supported OS, including parsers for Linux tool output, path and file-name handling, settings, rendering, input handling and the web API.

#### Scenario: v4l2 output parser on Windows
- **WHEN** the suite runs on Windows
- **THEN** the tests that parse recorded `v4l2-ctl` output run and pass

### Requirement: Coverage of simulated features
The suite SHALL include tests that exercise each simulated hardware piece and the main pipelines with it: every UI screen renders, button navigation between screens, finder images flow to the solver and telescope position, imaging capture and saving, settings updates through the web API, and a timed headless run of the full application.

#### Scenario: End-to-end smoke run
- **WHEN** the smoke test starts the application in `sim` with a short run limit
- **THEN** the process exits with status 0, the web UI answers, and at least one screen frame and one solve were produced

### Requirement: Tests do not change the working tree
Tests SHALL write only to temporary directories and SHALL NOT modify tracked files or device settings in the repository.

#### Scenario: Suite leaves repo clean
- **WHEN** the full suite finishes
- **THEN** `git status` shows no new or changed files

### Requirement: Continuous integration across operating systems
The repository SHALL run the test suite automatically on every push and pull request on Linux, macOS and Windows, for each supported Python version, without display or camera hardware.

#### Scenario: Pull request check
- **WHEN** a pull request is opened
- **THEN** test results are reported for each OS and Python version combination, with skipped tests listed by reason
