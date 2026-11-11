""" Ring-buffer store for captured images (finder + external imaging camera).
Each capture is <id>.jpg (preview) + <id>.json (metadata) + optional <id>.fits (raw data).
Only the most recent `max_kept` captures are kept. """
import io
import json
import os
import re
import threading
import time
from typing import Optional
import numpy as np
from PIL import Image
from utils import BASE_DIR

default_dir = os.path.join(BASE_DIR, "captures", "store")
_id_re = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9]{3}-(finder|imaging)$")


def to_preview(data: np.ndarray, max_size: int = 1600) -> Image.Image:
    """ Convert raw camera data (any bit depth, mono or RGB) into a displayable 8-bit image """
    arr = np.asarray(data)
    if arr.dtype != np.uint8:
        arr = arr.astype(np.float32)
        lo, hi = np.percentile(arr, (0.5, 99.8))
        if hi <= lo:
            hi = lo + 1
        arr = np.clip((arr - lo) / (hi - lo) * 255.0, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((max_size, max_size))
    return img


def jpeg_bytes(img: Image.Image, quality: int = 80) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


class CaptureStore:
    def __init__(self, directory: str = default_dir, max_kept: int = 50):
        self.directory = directory
        self.max_kept = max_kept
        self.lock = threading.Lock()
        os.makedirs(directory, exist_ok=True)

    @staticmethod
    def valid_id(capture_id: str) -> bool:
        return bool(_id_re.match(capture_id))

    def path(self, capture_id: str, ext: str) -> str:
        return os.path.join(self.directory, f"{capture_id}.{ext}")

    def save(self, data: np.ndarray, source: str, metadata: Optional[dict] = None, save_fits: bool = False) -> dict:
        now = time.time()
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime(now)) + f"-{int(now * 1000) % 1000:03d}"
        capture_id = f"{stamp}-{source}"
        arr = np.asarray(data)
        meta = {
            "id": capture_id,
            "source": source,
            "timestamp": now,
            "width": int(arr.shape[1]),
            "height": int(arr.shape[0]),
            "dtype": str(arr.dtype),
            "fits": False,
            **(metadata or {}),
        }
        with self.lock:
            to_preview(arr).save(self.path(capture_id, "jpg"), format="JPEG", quality=90)
            if save_fits:
                try:
                    from astropy.io import fits
                    hdu = fits.PrimaryHDU(arr if arr.ndim == 2 else np.moveaxis(arr, -1, 0))
                    for k, v in (("EXPTIME", meta.get("exposure_s")), ("GAIN", meta.get("gain")),
                                 ("XBINNING", meta.get("binning")), ("OBJECT", meta.get("target")),
                                 ("RA", meta.get("ra")), ("DEC", meta.get("dec"))):
                        if v is not None:
                            hdu.header[k] = v
                    hdu.writeto(self.path(capture_id, "fits"), overwrite=True)
                    meta["fits"] = True
                except Exception as e:
                    print(f"FITS save failed: {e}")
            with open(self.path(capture_id, "json"), "w", encoding="utf-8") as f:
                json.dump(meta, f)
            self._prune()
        return meta

    def _ids(self):
        ids = [f[:-5] for f in os.listdir(self.directory) if f.endswith(".json") and self.valid_id(f[:-5])]
        return sorted(ids, reverse=True)  # newest first (timestamped ids)

    def _prune(self):
        for capture_id in self._ids()[self.max_kept:]:
            self._remove(capture_id)

    def _remove(self, capture_id: str):
        for ext in ("jpg", "json", "fits"):
            try:
                os.remove(self.path(capture_id, ext))
            except FileNotFoundError:
                pass

    def list(self, source: Optional[str] = None):
        out = []
        for capture_id in self._ids():
            meta = self.get(capture_id)
            if meta and (source is None or meta.get("source") == source):
                out.append(meta)
        return out

    def get(self, capture_id: str) -> Optional[dict]:
        if not self.valid_id(capture_id):
            return None
        try:
            with open(self.path(capture_id, "json"), encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def delete(self, capture_id: str) -> bool:
        if self.get(capture_id) is None:
            return False
        with self.lock:
            self._remove(capture_id)
        return True

    def set_max_kept(self, n: int):
        with self.lock:
            self.max_kept = n
            self._prune()
