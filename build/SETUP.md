### Solvers
## Astrometry.net
Installed to system, requires index files.

## Tetra3
Installed via Python package manager (PIP). includes required files. 

## Cedar
An improvement/extension to Tetra3. 

Requires Rust/cargo (https://www.rust-lang.org/tools/install)

Uses new centroiding and solving functionality. 

Clone https://github.com/smroid/cedar-solve to home
Update PYTHONPATH:
`export PYTHONPATH=/home/pi/projects/cedar-solve/tetra3`

Clone https://github.com/smroid/cedar-detect to home
Enter `/cedar-detect` and build `cargo build --release`

Copy executable into cedar-solve
`cp /home/pi/cedar-detect/target/release/cedar-detect-server /home/pi/cedar-solve/tetra3/bin`

### Web control (hotspot)
Install deps: `pip install fastapi uvicorn websockets`

Create a hotspot on the Pi (NetworkManager) and start it on boot:
```
sudo nmcli dev wifi hotspot ifname wlan0 ssid Astroflo password <password>
sudo nmcli con modify Hotspot connection.autoconnect yes
sudo apt install avahi-daemon   # optional: http://rpi.local:8080
```
Join the `Astroflo` Wi-Fi and open `http://10.42.0.1:8080`. The server starts with `main.py`; port/host are under Settings → web (restart to apply).

Telescope (imaging) camera: Settings → imaging camera → backend
- `alpaca`: any ASCOM Alpaca camera server (e.g. ASCOM Remote, INDI Alpaca bridge, ZWO/QHY Alpaca drivers), set `alpaca_address` to `host:port`
- `uvc`: USB/UVC camera at `/dev/video<uvc_index>`

Develop off-Pi with simulated cameras: `python -m web.dev_server` → http://localhost:8080

### Running without hardware (Windows, macOS, Linux)
astroflo runs anywhere in the `sim` profile: the finder camera replays images from `test_data/`,
the imaging camera, solver, TFT display and buttons are simulated, and the web UI works as on the Pi.
Python 3.10 or newer.

```
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt        # Windows: .venv\Scripts\pip ...
.venv/bin/python main.py --profile sim               # web UI on http://localhost:8080
```
`python -m web.dev_server` does the same with its own settings file (`captures/dev_settings.json`).
In the web UI, Settings → Pi display shows the simulated screen with clickable A/B/L/R/U/D/C buttons.

**Profile**: chosen by `--profile`, then `ASTROFLO_PROFILE`, then `runtime.profile` in settings, then
hostname detection (`rpi` → `pi`, anything else → `sim`). Values: `auto`, `pi`, `sim`.

**Per-component backends** (settings → `runtime`, `auto` follows the profile):

| component | pi default | sim default | other choices |
|---|---|---|---|
| `finder_camera` | `rpi` (picamera2) | `images` | |
| `imaging_camera` | `sv105` | `fake` | `none` |
| `solver` | `cedar` | `fake` | `tetra3` (any OS, `pip install -r requirements-solver.txt`) |
| `display` | `tft` | `virtual` | |
| `input` | `gpio` (needs `tft`) | `sim` | |

Asking for a backend that cannot run here (e.g. `cedar` on Windows) stops startup with the reason.

**Other options**
- `finder_camera.source`: image file or folder replayed by the simulated finder camera (default `test_data`), `finder_camera.simulate_exposure`: wait for the exposure time per frame
- `runtime.fake_solve_ra` / `fake_solve_dec`: position reported by the fake solver
- `ASTROFLO_CEDAR_PATH` (or `runtime.cedar_path`): cedar-solve checkout, default `~/cedar-solve`
- `ASTROFLO_SNAPSHOT_DIR`: save virtual display frames there as PNGs (about one per second)
- `main.py --duration SECONDS` exits after that long; `--no-web`; `--port`; `--settings PATH`
- Matplotlib renders with Agg everywhere; set `MPLBACKEND` to override

**Data files**: `data/tyc.fits` is in the repo. Planet/asteroid ephemerides are not; without them
planet targets are disabled. Download `de440s.bsp` (and optionally `sb441-n16.bsp`) from
https://ssd.jpl.nasa.gov/ftp/eph/ into `data/`.

### Tests
```
pip install -r requirements-dev.txt
pytest                      # skipped tests are listed with the reason
pytest -m "not slow"        # skip the end-to-end run of main.py
```
Tests assume no camera, display or Pi. Markers skip tests whose needs are not met: `linux_only`,
`macos_only`, `windows_only`, `pi_only`, `requires_camera("finder"|"imaging")`, `requires_tft`,
`requires_v4l2`, `requires_tetra3`, `requires_ephemeris`. To run the real-hardware tests on the Pi:
```
ASTROFLO_HW_TESTS=1 pytest -m "pi_only or requires_camera or requires_tft"
```
CI (`.github/workflows/tests.yml`) runs the suite on Linux, macOS and Windows.
