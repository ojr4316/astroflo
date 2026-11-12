""" Run the full app off-Pi with simulated hardware and the web UI: python -m web.dev_server [main.py options]

Same as `python main.py --profile sim`, but keeps its settings in captures/dev_settings.json and
defaults the web imaging camera to the fake backend. PORT env var sets the web port.
"""
import os
import sys

from config import SettingsStore
from utils import BASE_DIR

DEV_SETTINGS = os.path.join(BASE_DIR, "captures", "dev_settings.json")


def main(argv=None) -> int:
    import main as app
    settings = SettingsStore(DEV_SETTINGS, legacy_path=None)
    if settings.settings.imaging_camera.backend == "none":
        settings.update({"imaging_camera": {"backend": "fake"}})
    args = ["--profile", "sim", "--settings", DEV_SETTINGS]
    if os.environ.get("PORT"):
        args += ["--port", os.environ["PORT"]]
    return app.main(args + list(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())
