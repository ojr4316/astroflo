"""
SV105 limits probe — run on the Pi with the SV105 plugged in.

Measures the exposure and gain the camera *actually* delivers (UVC cameras often advertise
more than they do), then writes data/sv105_limits.json, which the SV105 driver loads.

Usage (from the repo root):
    python3 tools/sv105_probe.py                 # full probe, writes data/sv105_limits.json
    python3 tools/sv105_probe.py --dry-run       # print results only
    python3 tools/sv105_probe.py --frames 5 --width 1280 --height 720

Scene: point at something dim and *uniform* that does not saturate at the longest exposure
(e.g. the scope with its dust cap on but not fully light-tight, or a dark room with a faint
light). If the table shows "SAT" at long exposures, dim the scene and re-run.

Requires: sudo apt install v4l-utils  (for v4l2-ctl)
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from capture import v4l2_util  # noqa: E402
from capture.sv105_camera import SV105Camera, LIMITS_FILE  # noqa: E402

GROWTH = 1.08          # a step must raise signal by >= 8% to count as "still effective"
SAT_LEVEL = 250


def measure(cam: SV105Camera, frames: int):
    """ Returns (mean, std, saturated_fraction, mean_frame_interval_s) over `frames` frames. """
    cam._flush()
    means, stds, sats, intervals = [], [], [], []
    last = time.perf_counter()
    for _ in range(frames):
        img = cam.capture()
        now = time.perf_counter()
        if img is None:
            raise RuntimeError("camera disconnected during probe")
        intervals.append(now - last)
        last = now
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
        means.append(gray.mean())
        stds.append(gray.std())
        sats.append(float((gray >= SAT_LEVEL).mean()))
    # first interval includes flush latency; drop it when we have more
    iv = intervals[1:] if len(intervals) > 1 else intervals
    return float(np.mean(means)), float(np.mean(stds)), float(np.mean(sats)), float(np.mean(iv))


def geometric(lo, hi, factor=2.0):
    vals, v = [], lo
    while v < hi:
        vals.append(v)
        v *= factor
    vals.append(hi)
    return vals


def last_effective(rows, key):
    """ Largest setting where the signal (or frame interval) still grew vs the previous step. """
    best = rows[0]["setting"]
    for prev, cur in zip(rows, rows[1:]):
        if cur["sat"] > 0.2:
            break  # saturated scene: can't judge further
        grew = cur[key] >= prev[key] * GROWTH
        slowed = key == "mean" and cur["interval"] >= prev["interval"] * GROWTH
        if grew or slowed:
            best = cur["setting"]
    return best


def print_table(title, rows, unit):
    print(f"\n{title}")
    print(f"{'setting':>14} {'mean':>7} {'std':>6} {'sat%':>6} {'frame s':>8}")
    for r in rows:
        flag = "  SAT" if r["sat"] > 0.2 else ""
        print(f"{r['setting']:>12.1f}{unit:>2} {r['mean']:7.1f} {r['std']:6.2f} {100 * r['sat']:6.2f} {r['interval']:8.3f}{flag}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frames", type=int, default=4, help="frames averaged per step")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fourcc", default="YUYV")
    ap.add_argument("--dry-run", action="store_true", help="don't write the limits file")
    ap.add_argument("--out", default=LIMITS_FILE)
    args = ap.parse_args()

    device = v4l2_util.find_device()
    if device is None:
        raise SystemExit("SV105 not found under /sys/class/video4linux (set ASTROFLO_SV105_DEVICE=/dev/videoN to override)")
    print(f"SV105 device: {device}")
    if not v4l2_util.has_v4l2_ctl():
        raise SystemExit("v4l2-ctl not found: sudo apt install v4l-utils")

    print("\n== Controls ==")
    print(v4l2_util.run_v4l2_ctl(device, "--list-ctrls-menus"))
    formats_text = v4l2_util.run_v4l2_ctl(device, "--list-formats-ext")
    print("== Formats ==")
    print(formats_text)

    # Start from reported ranges only (ignore any previous measurement)
    tmp_limits = {"width": args.width, "height": args.height, "fourcc": args.fourcc}
    tmp_file = os.path.join(os.path.dirname(args.out), ".sv105_probe_tmp.json")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(tmp_limits, f)

    cam = SV105Camera(limits_file=tmp_file)
    try:
        if not cam.connect():
            raise SystemExit("Could not open SV105")
        reported = cam.limits
        print(f"Reported limits: exposure {reported.min_exposure_us:.0f}-{reported.max_exposure_us:.0f} us, "
              f"gain {reported.min_gain:.0f}-{reported.max_gain:.0f}, fps options {cam.fps_options}")

        # 1. Exposure sweep at minimum gain
        exp_rows = []
        for exp in geometric(max(reported.min_exposure_us, 100.0), reported.max_exposure_us):
            cam.configure(exp, reported.min_gain)
            mean, std, sat, interval = measure(cam, args.frames)
            exp_rows.append({"setting": cam.exposure_us, "mean": mean, "std": std, "sat": sat, "interval": interval})
            print(f"  exposure {cam.exposure_us / 1000:9.1f} ms -> mean {mean:6.1f}  frame {interval:.3f}s")
        print_table("Exposure sweep (gain = min)", exp_rows, "us")
        max_exposure = last_effective(exp_rows, "mean")

        # 2. Gain sweep at a moderate exposure that is not saturated
        unsat = [r for r in exp_rows if r["mean"] < 60 and r["sat"] < 0.01]
        gain_exp = unsat[len(unsat) // 2]["setting"] if unsat else reported.min_exposure_us
        gain_rows = []
        steps = np.linspace(reported.min_gain, reported.max_gain, 11)
        for g in steps:
            cam.configure(gain_exp, float(g))
            mean, std, sat, interval = measure(cam, args.frames)
            gain_rows.append({"setting": cam.gain, "mean": mean, "std": std, "sat": sat, "interval": interval})
        print_table(f"Gain sweep (exposure = {gain_exp / 1000:.1f} ms)", gain_rows, "  ")
        # signal (mean) or noise (std) still growing means gain is still doing something
        max_gain_mean = last_effective(gain_rows, "mean")
        max_gain_std = last_effective(gain_rows, "std")
        max_gain = max(max_gain_mean, max_gain_std)

        result = {
            "width": args.width,
            "height": args.height,
            "fourcc": args.fourcc,
            "min_exposure_us": reported.min_exposure_us,
            "max_exposure_us": max_exposure,
            "min_gain": reported.min_gain,
            "max_gain": max_gain,
            "fps_options": cam.fps_options,
            "reported": {
                "max_exposure_us": reported.max_exposure_us,
                "max_gain": reported.max_gain,
            },
            "probed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "exposure_sweep": exp_rows,
            "gain_sweep": gain_rows,
        }
    finally:
        cam.close()
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

    print("\n== Result ==")
    print(f"Effective max exposure: {result['max_exposure_us'] / 1000:.1f} ms "
          f"(reported {result['reported']['max_exposure_us'] / 1000:.1f} ms)")
    print(f"Effective max gain:     {result['max_gain']:.0f} (reported {result['reported']['max_gain']:.0f})")
    if any(r["sat"] > 0.2 for r in result["exposure_sweep"]):
        print("WARNING: scene saturated during the exposure sweep; dim it and re-run for a trustworthy max.")

    if args.dry_run:
        print("(dry run: not written)")
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
