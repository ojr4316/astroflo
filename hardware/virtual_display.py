""" Headless stand-in for the TFT: keeps the latest rendered frame in memory (and optional PNG snapshots). """
import os
import threading
import time
from typing import Optional

from PIL import Image

WIDTH = HEIGHT = 240


class VirtualDisplay:
    def __init__(self, snapshot_dir: Optional[str] = None, snapshot_interval_s: float = 1.0):
        self.width, self.height = WIDTH, HEIGHT
        self.snapshot_dir = snapshot_dir
        self.snapshot_interval_s = snapshot_interval_s
        self.lock = threading.Lock()
        self.latest_frame: Optional[Image.Image] = None
        self.frame_count = 0
        self.snapshots_written = 0
        self.backlight = True
        self.brightness = 0
        self.overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        self._last_snapshot = 0.0
        if snapshot_dir:
            os.makedirs(snapshot_dir, exist_ok=True)
        print("Using virtual display" + (f" (snapshots in {snapshot_dir})" if snapshot_dir else ""))

    def set_brightness(self, b: float):
        """ Same dimming overlay as the TFT: 1 = full brightness, 0 = darkest """
        b = max(0.0, min(1.0, b))
        self.brightness = int((1.0 - b) * 255)
        self.overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, self.brightness))

    def set_backlight(self, on: bool):
        self.backlight = bool(on)

    def clear(self):
        with self.lock:
            self.latest_frame = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))

    def draw_screen(self, img: Optional[Image.Image]):
        if img is None:
            return
        frame = Image.alpha_composite(img.resize((WIDTH, HEIGHT)).convert("RGBA"), self.overlay).convert("RGB")
        with self.lock:
            self.latest_frame = frame
            self.frame_count += 1
        self._maybe_snapshot(frame)

    def get_frame(self) -> Optional[Image.Image]:
        with self.lock:
            return None if self.latest_frame is None else self.latest_frame.copy()

    def _maybe_snapshot(self, frame: Image.Image):
        if not self.snapshot_dir:
            return
        now = time.monotonic()
        if self.snapshots_written and now - self._last_snapshot < self.snapshot_interval_s:
            return
        self._last_snapshot = now
        frame.save(os.path.join(self.snapshot_dir, f"screen_{self.snapshots_written:05d}.png"))
        self.snapshots_written += 1

    def read_buttons(self, last_input):
        pass  # no physical buttons; see hardware.sim_input.SimInput
