"""Root pytest fixtures shared across unit/integration/e2e suites.

Anything placed here is auto-discovered for tests under tests/**, so
suites can share helpers without per-directory ``sys.path`` mutation
or cross-directory imports.

History:
  * 2026-05-25 (ARCH-003 fix-pass): promoted
    ``_build_mocked_real_sdk_camera`` from tests/unit/test_camera_service.py
    so the safety-cancellation integration test can drop its
    ``sys.path.insert(..., tests/unit)`` + cross-dir import hack.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from services.camera.asi_camera import ASICamera, CameraInfo


def _build_mocked_real_sdk_camera(
    tmp_data_dir: Path,
    width: int = 64,
    height: int = 48,
    bit_depth: int = 16,
) -> ASICamera:
    """Build a fully-mocked ASICamera that exercises the real-SDK branch.

    Sets up:
      - ``_camera`` mock supporting start_exposure / get_exposure_status /
        get_data_after_exposure
      - ``_asi`` mock with the ASI_EXP_SUCCESS / ASI_EXP_FAILED constants
      - ``_info`` populated with mono 16-bit defaults
      - ``get_roi()`` returning the requested width/height
      - ``_initialized = True`` so capture_single() does not bail

    The function form is preserved so tests that need to construct
    multiple cameras per test (or that want to share the helper with
    code outside the pytest fixture system) can still call it
    directly. The ``mocked_real_sdk_camera`` fixture below wraps it
    as a factory for the common single-camera case.
    """
    camera = ASICamera(camera_index=0, data_dir=tmp_data_dir)

    camera._asi = MagicMock()
    camera._asi.ASI_EXP_SUCCESS = 0
    camera._asi.ASI_EXP_FAILED = 1
    camera._asi.ASI_GAIN = 0
    camera._asi.ASI_EXPOSURE = 1
    camera._asi.ASI_BANDWIDTHOVERLOAD = 6
    camera._asi.ASI_HIGH_SPEED_MODE = 14
    camera._asi.ASI_FLIP = 17
    camera._asi.ASI_TEMPERATURE = 18
    camera._asi.ASI_TARGET_TEMP = 19
    camera._asi.ASI_COOLER_ON = 20
    camera._asi.ASI_COOLER_POWER_PERC = 21

    mock_cam = MagicMock()
    bytes_per_pixel = 2 if bit_depth > 8 else 1
    mock_cam.get_exposure_status.return_value = camera._asi.ASI_EXP_SUCCESS
    mock_cam.get_data_after_exposure.return_value = bytes(
        [1] * (width * height * bytes_per_pixel)
    )
    mock_cam.get_roi.return_value = (0, 0, width, height)
    camera._camera = mock_cam

    camera._info = CameraInfo(
        name="ZWO ASI Mock",
        camera_id=1,
        max_width=width,
        max_height=height,
        pixel_size_um=2.9,
        is_color=False,
        has_cooler=False,
        bit_depth=bit_depth,
        usb_host="USB3",
    )
    camera._initialized = True
    return camera


@pytest.fixture
def mocked_real_sdk_camera() -> Callable[..., ASICamera]:
    """Factory fixture: returns the camera builder for the test.

    Use:

        def test_x(tmp_path, mocked_real_sdk_camera):
            camera = mocked_real_sdk_camera(tmp_path, width=16, height=16)

    Factory rather than direct-camera fixture because the existing
    callers parametrize width/height/bit_depth per-test. A factory
    keeps that call-site flexibility without forcing every test into
    pytest.mark.parametrize.
    """
    return _build_mocked_real_sdk_camera
