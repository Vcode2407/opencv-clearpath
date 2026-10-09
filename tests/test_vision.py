import copy
import struct

import cv2
import numpy as np
import pytest

from clearpath.evaluate import evaluate
from clearpath.fixtures import FIXTURES, fixture_by_id, generate
from clearpath.vision import Calibration, decode_image, inspect, runtime_info


@pytest.fixture(scope="session", autouse=True)
def owned_fixture_images():
    generate()


def inspect_fixture(name):
    fixture = fixture_by_id(name)
    scene = cv2.imread(str(FIXTURES / fixture["image"]))
    reference = cv2.imread(str(FIXTURES / fixture["reference"]))
    return inspect(scene, reference, Calibration.from_dict(fixture["calibration"]))


def test_actual_opencv5_runtime_is_required_for_release():
    assert runtime_info()["opencv5_verified"], "Install the pinned OpenCV 5 wheel before calling this competition-ready."


@pytest.mark.parametrize("name,clearance,area", [
    ("clear", 2.4, 0), ("edge_boxes", 1.8, 0.89), ("pinch", 0.75, 1.65), ("blocked", 0, 1.68)
])
def test_measurements_match_independent_planar_fixture_dimensions(name, clearance, area):
    report, mask = inspect_fixture(name)
    assert report["status"] == "review_required"
    assert report["measurements"]["clearance_m"] == pytest.approx(clearance, abs=0.04)
    assert report["measurements"]["changed_area_m2"] == pytest.approx(area, abs=0.06)
    assert mask.shape == (600, 240)
    assert report["annotated_image"].startswith("data:image/png;base64,")


@pytest.mark.parametrize("name", ["blur", "glare", "shifted", "bad_geometry"])
def test_unreliable_capture_returns_request_instead_of_measurement(name):
    report, mask = inspect_fixture(name)
    assert report["status"] == "needs_capture"
    assert report["capture_requests"]
    assert report["measurements"] is None
    assert mask is None


def test_full_width_obstruction_has_no_connected_point_route():
    assert inspect_fixture("blocked")[0]["measurements"]["point_route_exists"] is False
    assert inspect_fixture("pinch")[0]["measurements"]["point_route_exists"] is True


def test_known_low_contrast_failure_is_exposed_in_evaluation():
    assessment = evaluate()
    case = next(case for case in assessment["cases"] if case["fixture"] == "low_contrast")
    assert case["known_limitation"]
    assert case["mask_iou"] == 0
    assert case["clearance_abs_error_m"] >= 0.9
    assert assessment["summary"]["status_correct"] == 9


def test_crossed_corners_are_not_measured():
    fixture = fixture_by_id("clear")
    raw = copy.deepcopy(fixture["calibration"])
    raw["points"][1], raw["points"][2] = raw["points"][2], raw["points"][1]
    scene = cv2.imread(str(FIXTURES / fixture["image"]))
    report, mask = inspect(scene, scene, Calibration.from_dict(raw))
    assert report["status"] == "needs_capture"
    assert mask is None


@pytest.mark.parametrize("field,value", [("width_m", float("nan")), ("length_m", 0), ("review_width_m", 9), ("points", [[0,0]])])
def test_invalid_calibration_input_is_rejected(field, value):
    raw = copy.deepcopy(fixture_by_id("clear")["calibration"])
    raw[field] = value
    with pytest.raises(ValueError):
        Calibration.from_dict(raw)


def test_image_decode_checks_pixel_budget_before_allocating():
    fake_png_header = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 100000, 100000)
    with pytest.raises(ValueError, match="8 megapixels"):
        decode_image(fake_png_header)


def test_image_decode_accepts_png_and_jpeg_and_rejects_other_data():
    image = np.full((100, 100, 3), 100, np.uint8)
    for format_name in (".png", ".jpg"):
        _, data = cv2.imencode(format_name, image)
        assert decode_image(data.tobytes()).shape == image.shape
    with pytest.raises(ValueError):
        decode_image(b"not an image")


def test_mismatched_reference_dimensions_are_rejected():
    scene = cv2.imread(str(FIXTURES / "clear.png"))
    with pytest.raises(ValueError, match="identical"):
        inspect(scene, scene[:500], Calibration.from_dict(fixture_by_id("clear")["calibration"]))
