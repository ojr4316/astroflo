""" External / telescope imaging camera (main camera at the telescope focus).
Separate from the finder (plate-solving) camera. Backends:
  - alpaca: any ASCOM Alpaca camera (ZWO/QHY/etc via ASCOM Remote, INDI->Alpaca bridges, ...)
  - uvc:    USB / UVC cameras via OpenCV (planetary webcams, guide cams)
  - fake:   synthetic star field for development """
import threading
import time
from abc import ABC, abstractmethod
from typing import Callable, Optional
import numpy as np


class ImagingBackend(ABC):
    name = "base"

    @abstractmethod
    def connect(self): ...

    @abstractmethod
    def disconnect(self): ...

    @abstractmethod
    def expose(self, exposure_s: float, gain: int, binning: int, abort: threading.Event) -> Optional[np.ndarray]:
        """ Blocking exposure; returns image (H, W[, 3]) or None if aborted """

    def info(self) -> dict:
        return {"backend": self.name}


class FakeImagingBackend(ImagingBackend):
    name = "fake"

    def __init__(self, size=(960, 1280)):
        self.size = size
        self.rng = np.random.default_rng()
        self.stars = [(self.rng.uniform(0, size[0]), self.rng.uniform(0, size[1]), self.rng.uniform(200, 4000))
                      for _ in range(80)]

    def connect(self): pass
    def disconnect(self): pass

    def expose(self, exposure_s, gain, binning, abort):
        end = time.time() + min(exposure_s, 5.0)  # cap simulated wait
        while time.time() < end:
            if abort.is_set():
                return None
            time.sleep(0.05)
        h, w = self.size[0] // binning, self.size[1] // binning
        img = self.rng.normal(800, 30, (h, w))
        yy, xx = np.mgrid[0:h, 0:w]
        for y, x, flux in self.stars:
            y, x = y / binning, x / binning
            if 3 < y < h - 3 and 3 < x < w - 3:
                ys, xs = slice(int(y) - 6, int(y) + 7), slice(int(x) - 6, int(x) + 7)
                img[ys, xs] += flux * exposure_s * (1 + gain / 100) * np.exp(
                    -((yy[ys, xs] - y) ** 2 + (xx[ys, xs] - x) ** 2) / 4.0)
        return np.clip(img, 0, 65535).astype(np.uint16)

    def info(self):
        return {"backend": self.name, "name": "Simulated camera", "width": self.size[1], "height": self.size[0]}


class AlpacaImagingBackend(ImagingBackend):
    name = "alpaca"

    def __init__(self, address: str, device: int = 0):
        self.address = address
        self.device = device
        self.cam = None

    def connect(self):
        from alpaca.camera import Camera  # alpyca
        self.cam = Camera(self.address, self.device)
        self.cam.Connected = True

    def disconnect(self):
        if self.cam is not None:
            try:
                self.cam.Connected = False
            finally:
                self.cam = None

    def expose(self, exposure_s, gain, binning, abort):
        cam = self.cam
        try:
            cam.BinX = binning
            cam.BinY = binning
            cam.NumX = cam.CameraXSize // binning
            cam.NumY = cam.CameraYSize // binning
            cam.StartX = 0
            cam.StartY = 0
        except Exception as e:
            print(f"Alpaca binning not applied: {e}")
        try:
            cam.Gain = gain
        except Exception:
            pass  # not all cameras support gain
        cam.StartExposure(exposure_s, True)
        while not cam.ImageReady:
            if abort.is_set():
                try:
                    cam.AbortExposure()
                except Exception:
                    pass
                return None
            time.sleep(0.1)
        img = np.array(cam.ImageArray)
        # Alpaca arrays are [x][y](\[plane]); convert to row-major (y, x)
        img = np.transpose(img, (1, 0, 2)) if img.ndim == 3 else img.T
        return img.astype(np.uint16 if img.max() > 255 else np.uint8)

    def info(self):
        out = {"backend": self.name, "address": self.address, "device": self.device}
        if self.cam is not None:
            for key, attr in (("name", "Name"), ("width", "CameraXSize"), ("height", "CameraYSize"),
                              ("temperature", "CCDTemperature"), ("max_bin", "MaxBinX")):
                try:
                    out[key] = getattr(self.cam, attr)
                except Exception:
                    pass
        return out


class UVCImagingBackend(ImagingBackend):
    name = "uvc"

    def __init__(self, index: int = 0):
        self.index = index
        self.cap = None

    def connect(self):
        import cv2
        self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            self.cap = None
            raise RuntimeError(f"Could not open /dev/video{self.index}")

    def disconnect(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def expose(self, exposure_s, gain, binning, abort):
        import cv2
        try:  # driver dependent; many UVC drivers use 100us units for manual exposure
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
            self.cap.set(cv2.CAP_PROP_EXPOSURE, exposure_s * 10_000)
            self.cap.set(cv2.CAP_PROP_GAIN, gain)
        except Exception:
            pass
        for _ in range(2):  # flush buffered frames taken with old settings
            self.cap.grab()
        if abort.is_set():
            return None
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("UVC frame read failed")
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if binning > 1:
            frame = cv2.resize(frame, (frame.shape[1] // binning, frame.shape[0] // binning), interpolation=cv2.INTER_AREA)
        return frame

    def info(self):
        out = {"backend": self.name, "index": self.index}
        if self.cap is not None:
            import cv2
            out["width"] = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            out["height"] = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return out


def build_backend(settings) -> Optional[ImagingBackend]:
    """ settings: config.ImagingCameraSettings """
    if settings.backend == "fake":
        return FakeImagingBackend()
    if settings.backend == "alpaca":
        return AlpacaImagingBackend(settings.alpaca_address, settings.alpaca_device)
    if settings.backend == "uvc":
        return UVCImagingBackend(settings.uvc_index)
    return None


class ImagingController:
    """ Runs exposures on a background thread and tracks status for the web UI """

    def __init__(self, on_image: Optional[Callable[[np.ndarray, dict], Optional[dict]]] = None,
                 backend_factory: Callable = build_backend):
        self.on_image = on_image  # (image, exposure metadata) -> saved capture metadata (or None)
        self.backend_factory = backend_factory
        self.backend: Optional[ImagingBackend] = None
        self.lock = threading.Lock()
        self.abort_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.latest_image: Optional[np.ndarray] = None
        self.latest_version = 0
        self.status = {"connected": False, "exposing": False, "error": None, "frame": 0, "frames": 0,
                       "exposure_started": None, "exposure_s": None, "last_capture": None, "info": {}}

    def connect(self, settings):
        self.disconnect()
        backend = self.backend_factory(settings)
        if backend is None:
            raise ValueError("Imaging camera backend is 'none'; choose one in settings")
        backend.connect()
        with self.lock:
            self.backend = backend
            self.status.update(connected=True, error=None, info=backend.info())

    def disconnect(self):
        self.abort()
        if self.thread is not None:
            self.thread.join(timeout=10)
        with self.lock:
            if self.backend is not None:
                try:
                    self.backend.disconnect()
                except Exception as e:
                    print(f"Imaging disconnect error: {e}")
            self.backend = None
            self.status.update(connected=False, exposing=False, info={})

    def start(self, exposure_s: float, gain: int, binning: int, count: int = 1, loop: bool = False, save: bool = True):
        with self.lock:
            if self.backend is None:
                raise RuntimeError("Imaging camera not connected")
            if self.status["exposing"]:
                raise RuntimeError("Exposure already in progress")
            self.abort_event.clear()
            self.status.update(exposing=True, error=None, frame=0, frames=0 if loop else count)
        self.thread = threading.Thread(target=self._run, args=(exposure_s, gain, binning, count, loop, save), daemon=True)
        self.thread.start()

    def abort(self):
        self.abort_event.set()

    def _run(self, exposure_s, gain, binning, count, loop, save):
        try:
            i = 0
            while (loop or i < count) and not self.abort_event.is_set():
                self.status.update(exposure_started=time.time(), exposure_s=exposure_s, frame=i + 1)
                img = self.backend.expose(exposure_s, gain, binning, self.abort_event)
                if img is None:
                    break
                self.latest_image = img
                self.latest_version += 1
                if save and self.on_image is not None:
                    meta = self.on_image(img, {"exposure_s": exposure_s, "gain": gain, "binning": binning,
                                               "camera": self.status["info"].get("name", self.backend.name)})
                    if meta:
                        self.status["last_capture"] = meta["id"]
                i += 1
        except Exception as e:
            self.status["error"] = str(e)
            print(f"Imaging error: {e}")
        finally:
            self.status.update(exposing=False, exposure_started=None)

    def get_status(self) -> dict:
        s = dict(self.status)
        if s["exposing"] and s["exposure_started"] and s["exposure_s"]:
            s["progress"] = min(1.0, (time.time() - s["exposure_started"]) / s["exposure_s"])
        else:
            s["progress"] = None
        s.pop("exposure_started", None)
        return s
