""" Platform detection, profile resolution and backend availability """
import pytest

import platform_info


@pytest.mark.parametrize("plat,linux,mac,win", [
    ("linux", True, False, False), ("darwin", False, True, False), ("win32", False, False, True)])
def test_os_detection(monkeypatch, plat, linux, mac, win):
    monkeypatch.setattr(platform_info.sys, "platform", plat)
    assert (platform_info.is_linux(), platform_info.is_macos(), platform_info.is_windows()) == (linux, mac, win)


@pytest.mark.parametrize("plat,node,expected", [
    ("linux", "rpi", True), ("linux", "laptop", False), ("win32", "rpi", False), ("darwin", "rpi", False)])
def test_is_pi(monkeypatch, plat, node, expected):
    monkeypatch.setattr(platform_info.sys, "platform", plat)
    monkeypatch.setattr(platform_info.platform, "node", lambda: node)
    assert platform_info.is_pi() is expected


def test_utils_reexports_is_pi():
    import utils
    assert utils.is_pi is platform_info.is_pi


def test_has_module():
    assert platform_info.has_module("json")
    assert not platform_info.has_module("definitely_not_a_module_xyz")


def test_v4l2_ctl_never_off_linux(monkeypatch):
    monkeypatch.setattr(platform_info.sys, "platform", "win32")
    monkeypatch.setattr(platform_info.shutil, "which", lambda name: "/usr/bin/" + name)
    assert not platform_info.has_v4l2_ctl()


# ---------- profile resolution and backends ----------
import backends  # noqa: E402
from config import Settings  # noqa: E402


def settings(**runtime):
    return Settings.model_validate({"runtime": runtime})


def as_pi(monkeypatch):
    monkeypatch.setattr(platform_info.sys, "platform", "linux")
    monkeypatch.setattr(platform_info.platform, "node", lambda: "rpi")


def test_profile_defaults_to_sim_off_pi(monkeypatch):
    monkeypatch.setattr(platform_info.platform, "node", lambda: "laptop")
    assert backends.resolve_profile("auto") == "sim"


def test_profile_defaults_to_pi_on_pi(monkeypatch):
    as_pi(monkeypatch)
    assert backends.resolve_profile("auto") == "pi"


def test_env_overrides_setting_and_detection(monkeypatch):
    as_pi(monkeypatch)
    monkeypatch.setenv("ASTROFLO_PROFILE", "sim")
    assert backends.resolve_profile("pi") == "sim"


def test_setting_overrides_detection(monkeypatch):
    as_pi(monkeypatch)
    assert backends.resolve_profile("sim") == "sim"


def test_invalid_profile_lists_allowed(monkeypatch):
    monkeypatch.setenv("ASTROFLO_PROFILE", "laptop")
    with pytest.raises(ValueError, match="auto, pi, sim"):
        backends.resolve_profile()


def test_sim_profile_backends():
    chosen = backends.resolve_backends(settings(profile="sim"))
    assert chosen == {"profile": "sim", **backends.PROFILE_DEFAULTS["sim"]}


def test_pi_profile_backends_when_hardware_available(monkeypatch):
    as_pi(monkeypatch)
    monkeypatch.setattr(platform_info, "has_module", lambda name: True)
    chosen = backends.resolve_backends(settings())
    assert chosen == {"profile": "pi", **backends.PROFILE_DEFAULTS["pi"]}


def test_component_override_keeps_other_defaults(monkeypatch):
    monkeypatch.setattr(platform_info, "has_module", lambda name: name == "tetra3")
    chosen = backends.resolve_backends(settings(profile="sim", solver="tetra3"))
    assert chosen["solver"] == "tetra3" and chosen["finder_camera"] == "images" and chosen["display"] == "virtual"


@pytest.mark.parametrize("component,name,needle", [
    ("finder_camera", "rpi", "finder_camera backend 'rpi'"),
    ("display", "tft", "display backend 'tft'"),
    ("solver", "cedar", "solver backend 'cedar'"),
    ("imaging_camera", "sv105", "imaging_camera backend 'sv105'"),
])
def test_unavailable_backend_fails_loudly_off_linux(monkeypatch, component, name, needle):
    monkeypatch.setattr(platform_info.sys, "platform", "win32")
    with pytest.raises(backends.BackendUnavailable, match=needle) as err:
        backends.resolve_backends(settings(profile="sim", **{component: name}))
    assert "Windows" in str(err.value)


def test_missing_package_named(monkeypatch):
    monkeypatch.setattr(platform_info, "has_module", lambda name: False)
    with pytest.raises(backends.BackendUnavailable, match="tetra3 is not installed"):
        backends.resolve_backends(settings(profile="sim", solver="tetra3"))


def test_gpio_input_requires_tft():
    with pytest.raises(backends.BackendUnavailable, match="TFT"):
        backends.resolve_backends(settings(profile="sim", input="gpio"))


def test_cedar_unavailable_without_checkout(monkeypatch, tmp_path):
    monkeypatch.setattr(platform_info.sys, "platform", "linux")
    monkeypatch.setenv("ASTROFLO_CEDAR_PATH", str(tmp_path / "nope"))
    monkeypatch.setattr(platform_info, "has_module", lambda name: False)
    assert "cedar-solve not found" in backends.REGISTRY["solver"]["cedar"].check(settings=settings())


def test_cedar_path_env_beats_setting(monkeypatch, tmp_path):
    monkeypatch.setenv("ASTROFLO_CEDAR_PATH", str(tmp_path))
    assert backends.cedar_path("/somewhere/else") == str(tmp_path)


def test_sim_backends_build_without_hardware_modules():
    from observation_context import ObservationContext
    s = settings(profile="sim")
    ctx = ObservationContext()
    chosen = backends.resolve_backends(s)
    built = {c: backends.build(c, chosen[c], ctx, s) for c in ("finder_camera", "imaging_camera", "solver", "display")}
    built["input"] = backends.build("input", chosen["input"], ctx, s, display=built["display"])
    assert {type(v).__name__ for v in built.values()} == {"ImageFolderCamera", "FakeImagingCamera", "FakeSolver",
                                                          "VirtualDisplay", "SimInput"}
    import sys
    assert not {"board", "digitalio", "picamera2"} & set(sys.modules)


def test_main_rejects_unavailable_backend(monkeypatch, capsys, isolated_files):
    import json
    import main
    path = isolated_files / "settings.json"
    path.write_text(json.dumps({"runtime": {"solver": "cedar"}}))
    monkeypatch.setattr(platform_info.sys, "platform", "darwin")
    assert main.main(["--profile", "sim", "--settings", str(path), "--no-web", "--duration", "0"]) == 2
    assert "solver backend 'cedar' is not available" in capsys.readouterr().err


def test_command_line_profile_beats_env(monkeypatch):
    monkeypatch.setenv("ASTROFLO_PROFILE", "pi")
    assert backends.resolve_profile("pi", override="sim") == "sim"
