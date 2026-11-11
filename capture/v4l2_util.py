""" Small helpers around Linux V4L2 (sysfs + v4l2-ctl) used by the SV105 driver and probe tool. """
import glob
import os
import re
import shutil
import subprocess
from typing import Dict, List, Optional

SV105_NAME_HINTS = ("sv105", "svbony")

# UVC exposure_absolute / exposure_time_absolute units are 100 microseconds
UVC_EXPOSURE_UNIT_US = 100.0


def find_device(name_hints=SV105_NAME_HINTS) -> Optional[str]:
    """ Find /dev/videoN whose sysfs name matches a hint. Skips metadata nodes (index != 0). """
    override = os.environ.get("ASTROFLO_SV105_DEVICE")
    if override:
        return override if os.path.exists(override) else None

    for node in sorted(glob.glob("/sys/class/video4linux/video*")):
        try:
            with open(os.path.join(node, "name"), encoding="utf-8") as f:
                name = f.read().strip().lower()
        except OSError:
            continue
        index_file = os.path.join(node, "index")
        if os.path.exists(index_file):
            with open(index_file, encoding="utf-8") as f:
                if f.read().strip() != "0":
                    continue
        if any(h in name for h in name_hints):
            return "/dev/" + os.path.basename(node)
    return None


def has_v4l2_ctl() -> bool:
    return shutil.which("v4l2-ctl") is not None


def run_v4l2_ctl(device: str, *args: str, timeout: float = 5.0) -> str:
    result = subprocess.run(["v4l2-ctl", "-d", device, *args],
                            capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"v4l2-ctl {' '.join(args)} failed")
    return result.stdout


_CTRL_RE = re.compile(r"^\s*(\w+)\s+0x[0-9a-f]+\s+\((\w+)\)\s*:\s*(.*)$")


def parse_ctrls(text: str) -> Dict[str, Dict[str, object]]:
    """ Parse `v4l2-ctl --list-ctrls` output into {name: {type, min, max, step, default, value, flags}}. """
    ctrls = {}
    for line in text.splitlines():
        m = _CTRL_RE.match(line)
        if not m:
            continue
        name, ctype, rest = m.groups()
        info: Dict[str, object] = {"type": ctype}
        for key, val in re.findall(r"(\w+)=(\S+)", rest):
            try:
                info[key] = int(val)
            except ValueError:
                info[key] = val
        ctrls[name] = info
    return ctrls


def list_ctrls(device: str) -> Dict[str, Dict[str, object]]:
    return parse_ctrls(run_v4l2_ctl(device, "--list-ctrls"))


def set_ctrls(device: str, **values):
    if values:
        run_v4l2_ctl(device, "--set-ctrl=" + ",".join(f"{k}={int(v)}" for k, v in values.items()))


def parse_frame_intervals(text: str) -> List[Dict[str, object]]:
    """
    Parse `v4l2-ctl --list-formats-ext` into a list of
    {fourcc, width, height, fps: [..]} entries.
    """
    modes = []
    fourcc = None
    current = None
    for line in text.splitlines():
        fmt = re.search(r"\[\d+\]:\s*'(\w+)'", line)
        if fmt:
            fourcc = fmt.group(1)
            continue
        size = re.search(r"Size:\s*Discrete\s*(\d+)x(\d+)", line)
        if size and fourcc:
            current = {"fourcc": fourcc, "width": int(size.group(1)), "height": int(size.group(2)), "fps": []}
            modes.append(current)
            continue
        interval = re.search(r"Interval:\s*Discrete\s*[\d.]+s\s*\(([\d.]+)\s*fps\)", line)
        if interval and current is not None:
            current["fps"].append(float(interval.group(1)))
    return modes


def exposure_ctrl_names(ctrls: Dict[str, Dict[str, object]]):
    """ Return (auto_ctrl, absolute_ctrl) names, handling old/new kernel naming. """
    auto = "auto_exposure" if "auto_exposure" in ctrls else ("exposure_auto" if "exposure_auto" in ctrls else None)
    absolute = ("exposure_time_absolute" if "exposure_time_absolute" in ctrls
                else ("exposure_absolute" if "exposure_absolute" in ctrls else None))
    return auto, absolute
