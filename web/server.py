""" Local web control for Astroflo. Join the device hotspot and open http://<pi-ip>:<port>/ """
import asyncio
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any, Literal, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field, ValidationError

from capture.capture_store import CaptureStore, jpeg_bytes, to_preview
from capture.imaging_camera import ImagingController
from config import SettingsStore
from observation_context import ObservationContext
from utils import distance_north_east, haversine_dist, radec_to_altaz

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@dataclass
class Services:
    ctx: ObservationContext
    settings: SettingsStore
    store: CaptureStore
    imaging: ImagingController
    catalog: Any = None       # astronomy.catalog.Catalog
    finder: Any = None        # capture.camera.Camera (plate-solving camera)
    ui: Any = None            # hardware.ui.UIManager (TFT display)
    starfield: Any = None     # astronomy.starfield.StarfieldRenderer
    analyzer: Any = None
    stellarium: Any = None
    on_settings_changed: Any = None  # callable(Settings) for main.py side effects


# ---------- request bodies ----------
class TargetBody(BaseModel):
    name: Optional[str] = None
    ra: Optional[float] = Field(None, ge=0, lt=360)
    dec: Optional[float] = Field(None, ge=-90, le=90)


class FinderCameraBody(BaseModel):
    exposure_us: Optional[int] = Field(None, ge=100, le=30_000_000)
    gain: Optional[float] = Field(None, ge=0, le=64)


class ExposeBody(BaseModel):
    exposure_s: Optional[float] = Field(None, ge=0.0001, le=3600)
    gain: Optional[int] = Field(None, ge=0)
    binning: Optional[int] = Field(None, ge=1, le=8)
    count: int = Field(1, ge=1, le=1000)
    loop: bool = False   # continuous preview / sequence until aborted
    save: bool = True    # store frames in capture ring buffer


class AlignmentBody(BaseModel):
    row: int = Field(..., ge=0)   # target pixel, (row, col) like SolverState.target_pixel
    col: int = Field(..., ge=0)


class DisplayBody(BaseModel):
    enabled: Optional[bool] = None
    brightness: Optional[float] = Field(None, ge=0, le=1)
    screen: Optional[str] = None


def _f(v):
    return None if v is None else float(v)


def _target_dict(t) -> dict:
    return {"name": str(t["Name"]), "ra": float(t["RAdeg"]), "dec": float(t["DEdeg"]),
            "mag": _f(t.get("Vmag")), "is_planet": bool(t.get("is_planet", False))}


def create_app(svc: Services) -> FastAPI:
    app = FastAPI(title="Astroflo", version="1.0")
    target_cache: dict = {}

    # ---------- helpers ----------
    def finder_frame() -> Optional[np.ndarray]:
        img = svc.ctx.camera_state.latest_image
        return None if img is None else np.asarray(img)

    def current_meta() -> dict:
        ts, tg = svc.ctx.telescope_state, svc.ctx.target_state
        meta = {"target": tg.name or None}
        if ts.position is not None:
            meta.update(ra=float(ts.position[0]), dec=float(ts.position[1]), roll=float(ts.roll))
        return meta

    def snapshot() -> dict:
        ctx = svc.ctx
        ts, tg, cam, solver = ctx.telescope_state, ctx.target_state, ctx.camera_state, ctx.solver_state
        from astropy.time import Time as AstropyTime
        now = AstropyTime.now()
        position = None
        if ts.position is not None:
            ra, dec = float(ts.position[0]), float(ts.position[1])
            position = {"ra": ra, "dec": dec, "roll": float(ts.roll)}
            try:
                alt, az = radec_to_altaz(ra, dec, now, ctx.environment.astropy_location)
                position.update(alt=float(alt), az=float(az))
            except Exception:
                pass
        target = None
        if tg.has_target():
            target = {"name": tg.name, "ra": float(tg.ra), "dec": float(tg.dec)}
            try:
                alt, az = radec_to_altaz(tg.ra, tg.dec, now, ctx.environment.astropy_location)
                target.update(alt=float(alt), az=float(az))
            except Exception:
                pass
            if position is not None:
                n, e = distance_north_east(position["ra"], position["dec"], tg.ra, tg.dec, position["roll"])
                target.update(north_deg=float(np.degrees(n)), east_deg=float(np.degrees(e)),
                              distance_deg=float(np.degrees(haversine_dist(position["ra"], position["dec"], tg.ra, tg.dec))))
        an = svc.analyzer
        focus = None
        if an is not None and an.fwhm_values:
            focus = {"fwhm": float(an.fwhm_values[-1]),
                     "min_fwhm": None if an.lowest_fwhm == float("inf") else float(an.lowest_fwhm),
                     "history": [float(v) for v in an.fwhm_values[-50:]]}
        ui = svc.ui
        return {
            "time": time.time(),
            "solved": ts.is_solved(),
            "last_solved_age": time.time() - solver.last_solved if solver.last_solved else None,
            "position": position,
            "target": target,
            "target_pixel": None if solver.target_pixel is None else [int(v) for v in solver.target_pixel],
            "finder_camera": {"exposure_us": _f(cam.exposure), "gain": _f(cam.gain), "has_image": cam.latest_image is not None,
                              "shape": None if cam.latest_image is None else list(np.shape(cam.latest_image)[:2])},
            "imaging_camera": svc.imaging.get_status(),
            "display": None if ui is None else {"enabled": ui.display_enabled, "brightness": ui.brightness,
                                                 "screen": ui.state_manager.state.name},
            "focus": focus,
            "optics": {"magnification": float(ctx.telescope_optics.magnification()),
                       "true_fov_deg": float(ctx.telescope_optics.field_radius() * 2),
                       "limiting_mag": float(ctx.telescope_optics.get_limiting_magnitude())},
        }

    # ---------- pages ----------
    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    if os.path.isdir(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # ---------- state ----------
    @app.get("/api/state")
    def get_state():
        return snapshot()

    @app.websocket("/ws/state")
    async def ws_state(ws: WebSocket):
        await ws.accept()
        try:
            while True:
                await ws.send_json(await asyncio.to_thread(snapshot))
                await asyncio.sleep(0.5)
        except (WebSocketDisconnect, RuntimeError):
            pass

    # ---------- finder (plate-solving) camera ----------
    def finder_jpeg(overlay: bool) -> bytes:
        frame = finder_frame()
        if frame is None:
            raise HTTPException(404, "No finder image yet")
        img = to_preview(frame).convert("RGB")
        tp = svc.ctx.solver_state.target_pixel
        if overlay and tp is not None:
            sx, sy = img.width / frame.shape[1], img.height / frame.shape[0]
            y, x, r = tp[0] * sy, tp[1] * sx, 10
            ImageDraw.Draw(img).ellipse([x - r, y - r, x + r, y + r], outline="red", width=2)
        return jpeg_bytes(img)

    @app.get("/api/finder/frame.jpg")
    def finder_frame_jpg(overlay: bool = True):
        return Response(finder_jpeg(overlay), media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    def mjpeg(get_bytes):
        fps = svc.settings.settings.web.stream_fps
        while True:
            try:
                data = get_bytes()
            except HTTPException:
                data = None
            if data:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n"
            time.sleep(1.0 / fps)

    @app.get("/api/finder/stream")
    def finder_stream(overlay: bool = True):
        return StreamingResponse(mjpeg(lambda: finder_jpeg(overlay)), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.post("/api/finder/camera")
    def finder_camera(body: FinderCameraBody):
        cam = svc.ctx.camera_state
        exposure = body.exposure_us if body.exposure_us is not None else int(cam.exposure)
        gain = body.gain if body.gain is not None else float(cam.gain)
        svc.settings.update({"finder_camera": {"exposure_us": exposure, "gain": gain}})
        if svc.finder is not None:
            threading.Thread(target=svc.finder.configure, args=(exposure, gain), daemon=True).start()
        else:
            cam.exposure, cam.gain = exposure, gain
        return {"exposure_us": exposure, "gain": gain}

    @app.post("/api/finder/capture")
    def finder_capture():
        frame = finder_frame()
        if frame is None:
            raise HTTPException(409, "No finder image yet")
        cam = svc.ctx.camera_state
        meta = {"exposure_s": float(cam.exposure) / 1e6, "gain": float(cam.gain), "camera": "finder", **current_meta()}
        return svc.store.save(frame.copy(), "finder", meta)

    @app.get("/api/starfield.png")
    def starfield_png():
        if svc.starfield is None:
            raise HTTPException(404, "Starfield unavailable")
        try:
            img, _ = svc.starfield.render()
        except Exception as e:
            raise HTTPException(500, f"Starfield render failed: {e}")
        if img is None:
            raise HTTPException(409, "Not solved yet")
        import io
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})

    # ---------- external / telescope imaging camera ----------
    @app.get("/api/imaging")
    def imaging_status():
        return {"status": svc.imaging.get_status(), "settings": svc.settings.settings.imaging_camera.model_dump()}

    @app.post("/api/imaging/connect")
    def imaging_connect():
        try:
            svc.imaging.connect(svc.settings.settings.imaging_camera)
        except Exception as e:
            svc.imaging.status["error"] = str(e)
            raise HTTPException(502, f"Connect failed: {e}")
        return svc.imaging.get_status()

    @app.post("/api/imaging/disconnect")
    def imaging_disconnect():
        svc.imaging.disconnect()
        return svc.imaging.get_status()

    @app.post("/api/imaging/expose")
    def imaging_expose(body: ExposeBody):
        s = svc.settings.settings.imaging_camera
        exposure = body.exposure_s if body.exposure_s is not None else s.exposure_s
        gain = body.gain if body.gain is not None else s.gain
        binning = body.binning if body.binning is not None else s.binning
        svc.settings.update({"imaging_camera": {"exposure_s": exposure, "gain": gain, "binning": binning}})
        try:
            svc.imaging.start(exposure, gain, binning, body.count, body.loop, body.save)
        except RuntimeError as e:
            raise HTTPException(409, str(e))
        return svc.imaging.get_status()

    @app.post("/api/imaging/abort")
    def imaging_abort():
        svc.imaging.abort()
        return svc.imaging.get_status()

    def imaging_jpeg() -> bytes:
        img = svc.imaging.latest_image
        if img is None:
            raise HTTPException(404, "No imaging frame yet")
        return jpeg_bytes(to_preview(img))

    @app.get("/api/imaging/frame.jpg")
    def imaging_frame():
        return Response(imaging_jpeg(), media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get("/api/imaging/stream")
    def imaging_stream():
        return StreamingResponse(mjpeg(imaging_jpeg), media_type="multipart/x-mixed-replace; boundary=frame")

    # ---------- targets ----------
    def load_targets(kind: str, mag: float):
        key = (kind, mag if kind != "solar" else None)
        hit = target_cache.get(key)
        if hit and time.time() - hit[0] < 60:
            return hit[1]
        if svc.catalog is None:
            raise HTTPException(503, "Catalog not loaded")
        if kind == "stars":
            raw = svc.catalog.get_bright_stars(mag)
        elif kind == "dsos":
            raw = svc.catalog.get_dsos(mag)
        else:
            raw = svc.catalog.get_solar_system()
        out = [_target_dict(t) for t in raw]
        target_cache[key] = (time.time(), out)
        return out

    @app.get("/api/targets")
    def targets(type: Literal["stars", "dsos", "solar"] = "stars", mag: float = 4.0, q: str = "", limit: int = 200):
        items = load_targets(type, mag)
        if q:
            ql = q.strip().lower()
            items = [t for t in items if ql in t["name"].lower()]
        return {"count": len(items), "items": items[:limit]}

    @app.get("/api/target")
    def get_target():
        return snapshot()["target"]

    @app.post("/api/target")
    def set_target(body: TargetBody):
        if body.ra is not None and body.dec is not None:
            ra, dec, name = body.ra, body.dec, body.name or f"RA {body.ra:.3f} Dec {body.dec:.3f}"
        elif body.name:
            found = None
            for kind, mag in (("solar", None), ("stars", 15.0), ("dsos", 15.0)):
                try:
                    found = next((t for t in load_targets(kind, mag) if t["name"].lower() == body.name.lower()), None)
                except Exception as e:
                    print(f"Target lookup in {kind} failed: {e}")
                    continue
                if found:
                    break
            if not found:
                raise HTTPException(404, f"Target '{body.name}' not found (or below horizon)")
            ra, dec, name = found["ra"], found["dec"], found["name"]
        else:
            raise HTTPException(422, "Provide name, or ra and dec")
        with svc.ctx.lock:
            svc.ctx.target_state.set_target(ra, dec, name)
        return snapshot()["target"]

    @app.delete("/api/target")
    def clear_target():
        with svc.ctx.lock:
            svc.ctx.target_state.set_target(None, None, "")
        return {"ok": True}

    # ---------- alignment ----------
    @app.post("/api/alignment")
    def set_alignment(body: AlignmentBody):
        with svc.ctx.lock:
            svc.ctx.solver_state.save_offset(np.array([body.row, body.col]))
        return {"target_pixel": [body.row, body.col]}

    # ---------- captures ----------
    @app.get("/api/captures")
    def list_captures(source: Optional[Literal["finder", "imaging"]] = None):
        return {"max_kept": svc.store.max_kept, "items": svc.store.list(source)}

    def capture_or_404(capture_id: str) -> dict:
        meta = svc.store.get(capture_id)
        if meta is None:
            raise HTTPException(404, "Capture not found")
        return meta

    @app.get("/api/captures/{capture_id}")
    def get_capture(capture_id: str):
        return capture_or_404(capture_id)

    @app.get("/api/captures/{capture_id}/image.jpg")
    def capture_jpg(capture_id: str, download: bool = False):
        capture_or_404(capture_id)
        return FileResponse(svc.store.path(capture_id, "jpg"), media_type="image/jpeg",
                            filename=f"{capture_id}.jpg" if download else None)

    @app.get("/api/captures/{capture_id}/image.fits")
    def capture_fits(capture_id: str):
        meta = capture_or_404(capture_id)
        if not meta.get("fits"):
            raise HTTPException(404, "No FITS for this capture")
        return FileResponse(svc.store.path(capture_id, "fits"), media_type="application/fits", filename=f"{capture_id}.fits")

    @app.delete("/api/captures/{capture_id}")
    def delete_capture(capture_id: str):
        if not svc.store.delete(capture_id):
            raise HTTPException(404, "Capture not found")
        return {"ok": True}

    # ---------- display (Pi TFT) ----------
    def display_state():
        ui = svc.ui
        if ui is None:
            raise HTTPException(503, "Display not available")
        from hardware.state import ScreenState
        return {"enabled": ui.display_enabled, "brightness": ui.brightness,
                "screen": ui.state_manager.state.name, "screens": [s.name for s in ScreenState]}

    @app.get("/api/display")
    def get_display():
        return display_state()

    @app.put("/api/display")
    def put_display(body: DisplayBody):
        ui = svc.ui
        if ui is None:
            raise HTTPException(503, "Display not available")
        ui.set_display(body.enabled, body.brightness)
        partial = {k: v for k, v in (("enabled", body.enabled), ("brightness", body.brightness)) if v is not None}
        if partial:
            svc.settings.update({"display": partial})
        if body.screen:
            from hardware.state import ScreenState
            try:
                state = ScreenState[body.screen]
            except KeyError:
                raise HTTPException(422, f"Unknown screen {body.screen}")
            threading.Thread(target=ui.set_screen, args=(state,), daemon=True).start()
        return display_state()

    # ---------- settings ----------
    @app.get("/api/settings")
    def get_settings():
        return svc.settings.settings.model_dump()

    @app.get("/api/settings/schema")
    def settings_schema():
        return svc.settings.settings.model_json_schema()

    @app.put("/api/settings")
    def put_settings(partial: dict):
        try:
            settings = svc.settings.update(partial)
        except ValidationError as e:
            raise HTTPException(422, e.errors(include_url=False, include_context=False))
        apply_settings(svc, settings, partial)
        return settings.model_dump()

    # ---------- system ----------
    @app.post("/api/system/{action}")
    def system(action: Literal["restart", "shutdown", "reboot"]):
        cmd = {"restart": ["sudo", "systemctl", "restart", "astroflo"],
               "reboot": ["sudo", "reboot"],
               "shutdown": ["sudo", "shutdown", "-h", "now"]}[action]
        try:
            subprocess.Popen(cmd)
        except Exception as e:
            raise HTTPException(500, str(e))
        return {"ok": True, "action": action}

    return app


def apply_settings(svc: Services, settings, partial: dict):
    """ Apply changed settings to live objects """
    svc.ctx.apply_settings(settings)
    if "location" in partial and svc.catalog is not None:
        try:
            svc.catalog.setup()  # rebuild topocentric observer
        except Exception as e:
            print(f"Catalog re-setup failed: {e}")
    if "finder_camera" in partial:
        fc = settings.finder_camera
        if svc.finder is not None:
            threading.Thread(target=svc.finder.configure, args=(fc.exposure_us, fc.gain), daemon=True).start()
    if "display" in partial and svc.ui is not None:
        svc.ui.set_display(settings.display.enabled, settings.display.brightness)
    if "captures" in partial:
        svc.store.set_max_kept(settings.captures.max_kept)
    if "integrations" in partial and svc.stellarium is not None:
        svc.stellarium.port = settings.integrations.stellarium_port
    if svc.on_settings_changed is not None:
        svc.on_settings_changed(settings)


def start_web_server(svc: Services) -> threading.Thread:
    import uvicorn
    web = svc.settings.settings.web
    config = uvicorn.Config(create_app(svc), host=web.host, port=web.port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    print(f"Web control on http://{web.host}:{web.port}/")
    return thread
