# image-storage Specification

## Purpose
Defines where and how imaging camera frames are written to disk so captures are organized by target and easy to find after a session.

## Requirements

### Requirement: Save directory by target
Captured images SHALL be saved under a `saves/` directory at the project root. Automatic captures SHALL go in a subdirectory named after the selected target; manual captures SHALL go in `saves/manual/`. Directories SHALL be created on demand.

#### Scenario: Automatic capture of a named target
- **WHEN** an automatic frame is captured while the target is "M42"
- **THEN** the file is written inside `saves/M42/`

#### Scenario: Manual capture
- **WHEN** a manual capture is taken, whether or not a target is selected
- **THEN** the file is written inside `saves/manual/`

#### Scenario: Directory missing
- **WHEN** the target subdirectory does not exist yet
- **THEN** it is created before the file is written

### Requirement: Target directory names are filesystem-safe
Target subdirectory names SHALL be derived from the target name by replacing characters that are not letters, digits, `-`, `_` or `.` with `_`, and trimming leading/trailing whitespace and dots. An empty result SHALL fall back to `unnamed`.

#### Scenario: Name with spaces and slashes
- **WHEN** the target name is "NGC 224 / Andromeda"
- **THEN** the directory is `saves/NGC_224___Andromeda/`

#### Scenario: Empty name
- **WHEN** the target name sanitizes to an empty string
- **THEN** the directory is `saves/unnamed/`

### Requirement: Timestamp file names
Each image file SHALL be named with its capture time in local time, formatted `YYYY-MM-DD_HH-MM-SS-mmm` (millisecond precision), followed by the image extension. Files SHALL be saved losslessly. A file SHALL never overwrite an existing file.

#### Scenario: Normal naming
- **WHEN** a frame is captured at 2026-11-11 21:04:05.123 local time
- **THEN** the file is named `2026-11-11_21-04-05-123.png`

#### Scenario: Name collision
- **WHEN** a file with the computed name already exists in the directory
- **THEN** the new file gets a numeric suffix (e.g. `2026-11-11_21-04-05-123_1.png`) and the existing file is unchanged

### Requirement: Saved images are excluded from version control
The `saves/` directory SHALL be ignored by git.

#### Scenario: Git status after imaging
- **WHEN** images have been saved and `git status` is run
- **THEN** no files under `saves/` are listed
