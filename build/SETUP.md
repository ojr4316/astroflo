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
