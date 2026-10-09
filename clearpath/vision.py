"""Actual CPU OpenCV analysis. A registered empty view is a required input.

Changed image regions are projected onto the calibrated floor plane. These are
approximate footprints only for flat objects/contact regions, not 3D segmentation.
"""
from __future__ import annotations

import base64
import struct
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

PIXELS_PER_METRE = 100
MAX_IMAGE_PIXELS = 8_000_000


@dataclass(frozen=True)
class Calibration:
    points: list[list[float]]
    width_m: float
    length_m: float
    review_width_m: float = 1.2

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Calibration":
        try:
            points = np.asarray(raw["points"], dtype=np.float64)
            width = float(raw["width_m"])
            length = float(raw["length_m"])
            target = float(raw.get("review_width_m", 1.2))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Supply four floor corners, measured width and length in metres.") from exc
        if points.shape != (4, 2) or not np.isfinite(points).all():
            raise ValueError("Calibration needs exactly four finite [x, y] image coordinates.")
        if not all(np.isfinite(v) for v in (width, length, target)):
            raise ValueError("Dimensions must be finite numbers.")
        if not (0.5 <= width <= 10 and 0.5 <= length <= 30 and 0.2 <= target <= 5):
            raise ValueError("Width must be 0.5–10 m, length 0.5–30 m, review target 0.2–5 m.")
        return cls(points.tolist(), width, length, target)


def decode_image(data: bytes) -> np.ndarray:
    if not data or len(data) > 8_000_000:
        raise ValueError("Each image must be non-empty and smaller than 8 MB.")
    # Check PNG/JPEG dimensions before OpenCV allocates the decoded pixel array.
    dimensions = None
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        dimensions = struct.unpack(">II", data[16:24])
    elif data.startswith(b"\xff\xd8"):
        offset = 2
        while offset + 4 <= len(data):
            if data[offset] != 0xFF:
                break
            while offset < len(data) and data[offset] == 0xFF:
                offset += 1
            if offset >= len(data):
                break
            marker = data[offset]
            offset += 1
            if marker in {0xD9, 0xDA}:
                break
            if marker in {0x01, *range(0xD0, 0xD9)}:
                continue
            if offset + 2 > len(data):
                break
            size = int.from_bytes(data[offset:offset + 2], "big")
            if size < 2 or offset + size > len(data):
                break
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF} and size >= 8:
                height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
                dimensions = (width, height)
                break
            offset += size
    if not dimensions or min(dimensions) <= 0:
        raise ValueError("Could not read image dimensions. Use a PNG or JPEG.")
    if dimensions[0] * dimensions[1] > MAX_IMAGE_PIXELS:
        raise ValueError("Resize the image to at most 8 megapixels before inspecting.")
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.ndim != 3:
        raise ValueError("Could not decode the image. Use a PNG or JPEG.")
    if image.shape[0] * image.shape[1] > MAX_IMAGE_PIXELS:
        raise ValueError("Resize the image to at most 8 megapixels before inspecting.")
    return image


def png_data(image: np.ndarray) -> str:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Could not encode image evidence.")
    return "data:image/png;base64," + base64.b64encode(encoded).decode("ascii")


def runtime_info() -> dict[str, Any]:
    major = int(cv2.__version__.split(".")[0])
    return {"opencv_version": cv2.__version__, "opencv5_verified": major == 5,
            "compute": "CPU", "ai_provider": "none",
            "aws_deployment_verified": False}


def _geometry(cal: Calibration, image_shape: tuple) -> tuple[list[str], np.ndarray]:
    points = np.asarray(cal.points, dtype=np.float32)
    height, width = image_shape[:2]
    problems: list[str] = []
    if np.any(points < 0) or np.any(points[:, 0] >= width) or np.any(points[:, 1] >= height):
        problems.append("All four corners must be inside the photograph.")
    signed_area = float(cv2.contourArea(points, oriented=True))
    if not cv2.isContourConvex(points) or signed_area <= 0:
        problems.append("Select a convex floor rectangle clockwise: far-left, far-right, near-right, near-left.")
    area_fraction = abs(signed_area) / (height * width)
    lengths = np.linalg.norm(points - np.roll(points, 1, axis=0), axis=1)
    if area_fraction < 0.05 or lengths.min() < 40 or lengths.max() / max(lengths.min(), 1) > 12:
        problems.append("The floor rectangle is too small or foreshortened. Move nearer and use a more overhead angle.")
    return problems, points


def _free_spans(row: np.ndarray) -> list[tuple[int, int]]:
    free = np.pad(row == 0, (1, 1), constant_values=False)
    changes = np.diff(free.astype(np.int8))
    return list(zip(np.flatnonzero(changes == 1).tolist(), np.flatnonzero(changes == -1).tolist()))


def _measurement(mask: np.ndarray, metres_per_pixel: float, width_m: float) -> dict[str, Any]:
    row_spans = [_free_spans(row) for row in mask]
    widest = [max((end - start for start, end in spans), default=0) for spans in row_spans]
    bottleneck_row = int(np.argmin(widest))
    spans = row_spans[bottleneck_row]
    widest_span = max(spans, key=lambda item: item[1] - item[0], default=(0, 0))
    # Connectivity checks only a point-sized route. It is not a traversable body-width claim.
    _, labels = cv2.connectedComponents((mask == 0).astype(np.uint8), connectivity=8)
    first = set(labels[0].tolist()) - {0}
    last = set(labels[-1].tolist()) - {0}
    point_route = bool(first & last)
    count, component_labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    obstacles: list[dict[str, Any]] = []
    for label in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[label])
        obstacles.append({"id": label, "area_m2": round(area * metres_per_pixel ** 2, 4),
                          "bounds_m": [round(v * metres_per_pixel, 3) for v in (x, y, w, h)]})
    return {"clearance_m": round(min(width_m, widest[bottleneck_row] * metres_per_pixel), 3),
            "bottleneck_y_m": round(bottleneck_row * metres_per_pixel, 3),
            "bottleneck_span_px": list(widest_span), "bottleneck_row_px": bottleneck_row,
            "point_route_exists": point_route,
            "changed_area_m2": round(np.count_nonzero(mask) * metres_per_pixel ** 2, 4),
            "obstacle_count": len(obstacles), "obstacles": obstacles}


def inspect(scene: np.ndarray, reference: np.ndarray, cal: Calibration) -> tuple[dict, np.ndarray | None]:
    """Return a serializable report and an occupancy mask for independent evaluation."""
    if scene.shape != reference.shape:
        raise ValueError("Scene and empty reference must have identical image dimensions and camera pose.")
    if scene.dtype != np.uint8 or scene.ndim != 3 or scene.shape[2] != 3:
        raise ValueError("Expected three-channel 8-bit images.")
    report: dict[str, Any] = {
        "runtime": runtime_info(), "status": "needs_capture", "measurements": None,
        "quality": {}, "capture_requests": [], "trace": [],
        "calibration": {"points": cal.points, "width_m": cal.width_m, "length_m": cal.length_m,
                        "review_width_m": cal.review_width_m},
        "method": "Registered empty-reference difference, calibrated floor homography, morphology, connected components",
        "limitations": [
            "Measurements describe projected changed regions, not semantic objects or full 3D footprints.",
            "Flat/contact regions, a planar floor, measured corners and an unchanged camera are required.",
            "Low-contrast obstacles, shadows, reflective surfaces and occlusion can cause missed or false regions.",
            "Clearance is the smallest widest free cross-section; it is not a continuous body-width route guarantee.",
            "This is a review aid. It does not certify accessibility, compliance or safety.",
        ],
    }
    problems, points = _geometry(cal, scene.shape)
    report["trace"].append({"step": "validate_geometry", "outcome": "retry" if problems else "accepted"})
    annotated = scene.copy()
    cv2.polylines(annotated, [points.astype(np.int32)], True, (70, 200, 220), 3)
    if problems:
        report["capture_requests"] = problems
        report["annotated_image"] = png_data(annotated)
        return report, None
    floor_mask = np.zeros(scene.shape[:2], dtype=np.uint8)
    cv2.fillConvexPoly(floor_mask, points.astype(np.int32), 255)
    roi = cv2.erode(floor_mask, np.ones((15, 15), dtype=np.uint8)) > 0
    gray = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY)
    ref_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    focus = float(cv2.Laplacian(gray, cv2.CV_64F)[roi].var())
    ref_focus = float(cv2.Laplacian(ref_gray, cv2.CV_64F)[roi].var())
    clipping = float(np.mean((gray[roi] >= 250) | (gray[roi] <= 5)))
    outside = floor_mask == 0
    outside_delta = float(np.mean(cv2.absdiff(scene, reference)[outside])) if outside.any() else 0.0
    shift, registration_response = cv2.phaseCorrelate(ref_gray.astype(np.float32), gray.astype(np.float32))
    report["quality"] = {"focus_variance": round(focus, 2), "reference_focus_variance": round(ref_focus, 2),
                          "clipped_fraction": round(clipping, 4), "outside_difference": round(outside_delta, 2),
                          "registration_shift_px": [round(v, 2) for v in shift],
                          "registration_response": round(registration_response, 4)}
    if min(focus, ref_focus) < 45:
        report["capture_requests"].append("Retake the scene and empty reference in focus; keep the same camera position.")
    if clipping > 0.22:
        report["capture_requests"].append("Retake from an angle without glare or deep shadow; keep the reference aligned.")
    if outside_delta > 18 or (registration_response > 0.2 and np.linalg.norm(shift) > 3):
        report["capture_requests"].append("The background changed. Restore the original camera pose and lighting, then capture a new aligned pair.")
    report["trace"].append({"step": "check_capture_quality", "outcome": "retry" if report["capture_requests"] else "accepted"})
    if report["capture_requests"]:
        report["annotated_image"] = png_data(annotated)
        return report, None
    out_w = int(round(cal.width_m * PIXELS_PER_METRE))
    out_h = int(round(cal.length_m * PIXELS_PER_METRE))
    dest = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], np.float32)
    transform = cv2.getPerspectiveTransform(points, dest)
    rectified = cv2.warpPerspective(scene, transform, (out_w, out_h))
    empty = cv2.warpPerspective(reference, transform, (out_w, out_h))
    difference = cv2.absdiff(rectified, empty).max(axis=2)
    occupancy = (difference > 35).astype(np.uint8) * 255
    occupancy = cv2.morphologyEx(occupancy, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    occupancy = cv2.morphologyEx(occupancy, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(occupancy)
    for label in range(1, n):
        if stats[label, cv2.CC_STAT_AREA] < 40:  # 0.004 m² at the fixed analysis scale
            occupancy[labels == label] = 0
    changed_fraction = float(np.mean(occupancy > 0))
    report["quality"]["changed_fraction"] = round(changed_fraction, 4)
    if changed_fraction > 0.60:
        report["capture_requests"].append("Most of the floor changed. Check alignment, lighting and the empty reference before measuring.")
        report["trace"].append({"step": "check_reference_agreement", "outcome": "retry"})
        report["annotated_image"] = png_data(annotated)
        report["rectified_image"] = png_data(rectified)
        return report, None
    measurements = _measurement(occupancy, 1 / PIXELS_PER_METRE, cal.width_m)
    measurements["review_width_m"] = cal.review_width_m
    measurements["below_review_target"] = measurements["clearance_m"] < cal.review_width_m
    report["measurements"] = measurements
    report["status"] = "review_required"
    report["trace"].extend([
        {"step": "project_floor", "outcome": f"{out_w} × {out_h} pixels; nominal 1 cm sampling"},
        {"step": "measure_changed_regions", "outcome": f"{measurements['obstacle_count']} regions; {measurements['clearance_m']:.2f} m cross-section"},
        {"step": "request_human_review", "outcome": "Review the region overlay, calibration and limitations before using the measurements."},
    ])
    contours, _ = cv2.findContours(occupancy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    overlay = rectified.copy()
    overlay[occupancy > 0] = (overlay[occupancy > 0] * 0.35 + np.array([45, 85, 235]) * 0.65).astype(np.uint8)
    cv2.drawContours(overlay, contours, -1, (40, 70, 245), 2)
    row = measurements["bottleneck_row_px"]
    start, end = measurements["bottleneck_span_px"]
    cv2.line(overlay, (start, row), (max(start, end - 1), row), (65, 215, 125), 3)
    inverse = np.linalg.inv(transform)
    for contour in contours:
        projected = cv2.perspectiveTransform(contour.astype(np.float32), inverse).astype(np.int32)
        cv2.drawContours(annotated, [projected], -1, (40, 70, 245), 3)
    cv2.putText(annotated, f"REVIEW: {measurements['clearance_m']:.2f} m cross-section", (24, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (245, 245, 245), 2, cv2.LINE_AA)
    report["annotated_image"] = png_data(annotated)
    report["rectified_image"] = png_data(overlay)
    report["occupancy_image"] = png_data(occupancy)
    return report, occupancy
