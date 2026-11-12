""" End-to-end: run the whole app headless in the sim profile as a separate process """
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.slow
def test_headless_sim_run(tmp_path):
    port = free_port()
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({
        "integrations": {"stellarium_enabled": False},
        "web": {"host": "127.0.0.1", "port": port},
        "finder_camera": {"exposure_us": 100_000},
    }))
    snapshots = tmp_path / "snapshots"
    env = dict(os.environ, ASTROFLO_SNAPSHOT_DIR=str(snapshots), PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    env.pop("ASTROFLO_PROFILE", None)
    proc = subprocess.Popen([sys.executable, "main.py", "--profile", "sim", "--duration", "8", "--settings", str(settings)],
                            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    state = None
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and proc.poll() is None:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=2) as r:
                    state = json.load(r)
                break
            except OSError:
                time.sleep(0.3)
        out, _ = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 0, out
    assert "astroflo profile: sim" in out
    assert state is not None and "position" in state, f"web API never answered\n{out}"
    assert list(snapshots.glob("*.png")), "no screen frames rendered"
    solves = re.search(r"solves: (\d+)", out)
    assert solves and int(solves.group(1)) >= 1, out
    assert not (settings.parent / "settings.json.tmp").exists()
