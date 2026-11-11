from capture.fake_imaging_camera import FakeImagingCamera
from capture import v4l2_util

CTRLS = """
User Controls

                     brightness 0x00980900 (int)    : min=-64 max=64 step=1 default=0 value=0
                           gain 0x00980913 (int)    : min=0 max=100 step=1 default=0 value=0

Camera Controls

                  auto_exposure 0x009a0901 (menu)   : min=0 max=3 default=3 value=3 (Aperture Priority Mode)
         exposure_time_absolute 0x009a0902 (int)    : min=1 max=5000 step=1 default=157 value=157 flags=inactive
     exposure_dynamic_framerate 0x009a0903 (bool)   : default=0 value=0
"""

FORMATS = """
ioctl: VIDIOC_ENUM_FMT
	Type: Video Capture

	[0]: 'MJPG' (Motion-JPEG, compressed)
		Size: Discrete 1920x1080
			Interval: Discrete 0.033s (30.000 fps)
	[1]: 'YUYV' (YUYV 4:2:2)
		Size: Discrete 1920x1080
			Interval: Discrete 0.200s (5.000 fps)
			Interval: Discrete 1.000s (1.000 fps)
		Size: Discrete 640x480
			Interval: Discrete 0.033s (30.000 fps)
"""


def test_parse_ctrls():
    ctrls = v4l2_util.parse_ctrls(CTRLS)
    assert ctrls["gain"]["max"] == 100
    assert ctrls["exposure_time_absolute"]["max"] == 5000
    assert v4l2_util.exposure_ctrl_names(ctrls) == ("auto_exposure", "exposure_time_absolute")


def test_parse_frame_intervals():
    modes = v4l2_util.parse_frame_intervals(FORMATS)
    yuyv = [m for m in modes if m["fourcc"] == "YUYV" and m["width"] == 1920]
    assert yuyv[0]["fps"] == [5.0, 1.0]


def test_fake_camera_disconnect():
    cam = FakeImagingCamera()
    assert cam.connect()
    assert cam.capture() is not None
    cam.present = False
    assert not cam.is_connected()
    assert cam.capture() is None
    cam.present = True
    assert cam.connect()


def test_fake_camera_clamps_settings():
    cam = FakeImagingCamera()
    cam.configure(1e12, 1e6)
    assert cam.exposure_us == cam.limits.max_exposure_us
    assert cam.gain == cam.limits.max_gain
