""" astroflo entry point.

    python main.py                        # auto: real hardware on the Pi, simulated hardware elsewhere
    python main.py --profile sim          # simulated cameras/solver/display/buttons on any OS
    python main.py --profile sim --duration 10 --no-web
"""
import os

# Off-screen rendering only (frames go to the TFT/virtual display/web as images): Agg is the
# thread-safe choice on every OS. Set MPLBACKEND to override. Must happen before pyplot loads.
os.environ.setdefault("MPLBACKEND", "Agg")

import argparse
import sys
import threading
import time

import backends
from observation_context import ObservationContext, TelescopeState, TargetState
from hardware.ui import UIManager
from astronomy.catalog import Catalog
from astronomy.starfield import StarfieldRenderer
from analyzer import analyzer
from config import SettingsStore
from capture.capture_store import CaptureStore
from capture.imaging import ImagingController
from capture.remote_imaging import ImagingController as RemoteImagingController

drift_field = True


def try_set_target(catalog: Catalog, target_state: TargetState, name: str):
    target = catalog.search_by_name(name, False)
    if len(target) > 0:
        target = target[0]
        target_state.set_target(target['RAdeg'], target['DEdeg'], target['Name'])
        print(f"Target set to {target['Name']} at RA: {target['RAdeg']}, DEC: {target['DEdeg']}")
    else:
        print(f"Target '{name}' not found in catalog.")


def try_set_planet(catalog: Catalog, target_state: TargetState, name: str):
    planet = catalog.get_current_position(name)
    if planet:
        target_state.set_target(planet['RAdeg'], planet['DEdeg'], planet['Name'])
        print(f"Target set to {planet['Name']} at RA: {planet['RAdeg']}, DEC: {planet['DEdeg']}")
    else:
        print(f"Planet '{name}' not found in catalog.")


last_time = None
def running(telescope_state: TelescopeState):
    global last_time
    now = time.perf_counter()
    delta = now - last_time if last_time is not None else 0
    last_time = now
    if drift_field:
        telescope_state.sky_drift(delta)
    time.sleep(0.05)


def start_web(ctx, settings, catalog, camera, ui, starfield):
    global drift_field
    try:
        from web.server import Services, start_web_server
    except ImportError as e:
        print(f"Web control disabled (missing dependency: {e})")
        return None

    store = CaptureStore(max_kept=settings.settings.captures.max_kept)

    def on_imaging_frame(image, meta):
        tg, ts = ctx.target_state, ctx.telescope_state
        meta = dict(meta, target=tg.name or None)
        if ts.position is not None:
            meta.update(ra=float(ts.position[0]), dec=float(ts.position[1]))
        return store.save(image, "imaging", meta, save_fits=settings.settings.imaging_camera.save_fits)

    def on_settings_changed(s):
        global drift_field
        drift_field = s.integrations.sky_drift

    svc = Services(ctx=ctx, settings=settings, store=store, imaging=RemoteImagingController(on_imaging_frame),
                   catalog=catalog, finder=camera, ui=ui, starfield=starfield, analyzer=analyzer,
                   stellarium=ctx.telescope_state.stel, on_settings_changed=on_settings_changed)
    start_web_server(svc)
    return svc


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="astroflo telescope assistant")
    p.add_argument("--profile", choices=["auto", *backends.PROFILES],
                   help="hardware profile (default: ASTROFLO_PROFILE, then settings, then Pi detection)")
    p.add_argument("--duration", type=float, default=None, help="exit after this many seconds")
    p.add_argument("--no-web", action="store_true", help="do not start the web server")
    p.add_argument("--port", type=int, default=None, help="web server port (overrides settings)")
    p.add_argument("--settings", default=None, help="settings.json path (default: repo settings.json)")
    return p.parse_args(argv)


def start_thread(threads, target, *args, name=None):
    thread = threading.Thread(target=target, args=args, name=name, daemon=True)
    thread.start()
    threads.append(thread)
    return thread


def main(argv=None) -> int:
    global drift_field
    args = parse_args(argv)

    settings = SettingsStore(args.settings) if args.settings else SettingsStore()
    if args.port:
        settings.settings.web.port = args.port  # not persisted
    try:
        chosen = backends.resolve_backends(settings.settings, args.profile)
    except (ValueError, backends.BackendUnavailable) as e:
        print(f"Startup failed: {e}", file=sys.stderr)
        return 2
    print(f"astroflo profile: {chosen['profile']}" + (" (simulating hardware)" if chosen["profile"] == "sim" else "")
          + " | " + ", ".join(f"{c}={chosen[c]}" for c in backends.COMPONENTS))

    ctx = ObservationContext()
    ctx.apply_settings(settings.settings)
    drift_field = settings.settings.integrations.sky_drift
    ctx.telescope_state.stel.port = settings.settings.integrations.stellarium_port
    catalog = Catalog(ctx.environment)

    #try_set_planet(catalog, ctx.target_state, "Jupiter")
    #ctx.target_state.set_target(213.915416, 19.1822222, "Arcturus")
    starfield = StarfieldRenderer(
        catalog=catalog,
        telescope_state=ctx.telescope_state,
        telescope_optics=ctx.telescope_optics,
        target_state=ctx.target_state
    )

    def build(component, **kwargs):
        return backends.build(component, chosen[component], ctx, settings.settings, **kwargs)

    display = build("display")
    ui = UIManager(ctx, starfield, display=display, buttons=build("input", display=display))
    ui.set_display(settings.settings.display.enabled, settings.settings.display.brightness)

    camera = build("finder_camera")
    solver = build("solver")
    stop_event = ui.stop_event

    threads = []
    start_thread(threads, camera.capturer, name="finder-camera")
    start_thread(threads, solver.solver, camera.queue, stop_event, name="solver")
    start_thread(threads, ui.draw_screen, name="ui-draw")
    start_thread(threads, ui.handle_input, name="ui-input")
    start_thread(threads, analyzer.process, name="analyzer")

    imaging_camera = build("imaging_camera")
    imaging = None
    if imaging_camera is not None:
        imaging = ImagingController(imaging_camera, ctx)
        start_thread(threads, imaging.run, name="imaging")

    if settings.settings.integrations.stellarium_enabled:
        ctx.telescope_state.stel.run_server()

    if not args.no_web:
        start_web(ctx, settings, catalog, camera, ui, starfield)

    deadline = None if args.duration is None else time.monotonic() + args.duration
    try:
        while deadline is None or time.monotonic() < deadline:
            running(ctx.telescope_state)
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        print("Shutting down")
        stop_event.set()
        camera.running = False
        if imaging is not None:
            imaging.stop()
        join_deadline = time.monotonic() + 3.0  # daemon threads still blocked after this die with the process
        for thread in threads:
            thread.join(timeout=max(0.0, join_deadline - time.monotonic()))
        print(f"Stopped (solves: {solver.solves}, screen frames: {getattr(display, 'frame_count', 'n/a')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
