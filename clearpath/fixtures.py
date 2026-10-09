"""Owned deterministic scientific fixtures, not photographs or a training dataset."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def generate(destination: Path = FIXTURES) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    width_px, height_px = 240, 600
    rng = np.random.default_rng(20261010)
    floor = np.full((height_px, width_px, 3), 148, np.uint8)
    noise = rng.integers(-9, 10, size=(height_px, width_px, 1), dtype=np.int16)
    floor = np.clip(floor.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    for y in range(0, height_px, 40):
        cv2.line(floor, (0, y), (width_px - 1, y), (112, 114, 116), 1)
    for x in range(0, width_px, 40):
        cv2.line(floor, (x, 0), (x, height_px - 1), (112, 114, 116), 1)
    corners = np.array([[290, 82], [610, 82], [812, 630], [88, 630]], np.float32)
    source = np.array([[0, 0], [239, 0], [239, 599], [0, 599]], np.float32)
    transform = cv2.getPerspectiveTransform(source, corners)
    base = np.full((700, 900, 3), (49, 57, 59), np.uint8)
    # Background fiducials make shifted-camera failure observable.
    for x in range(30, 900, 80):
        cv2.circle(base, (x, 36), 8, (120, 138, 143), -1)
    image_mask = cv2.warpPerspective(np.full((600, 240), 255, np.uint8), transform, (900, 700))

    def photograph(flat):
        warped = cv2.warpPerspective(flat, transform, (900, 700))
        image = base.copy()
        image[image_mask > 0] = warped[image_mask > 0]
        return image

    reference = photograph(floor)
    cv2.imwrite(str(destination / "reference.png"), reference)
    scenarios = [
        ("clear", "Empty walkway", [], None),
        ("edge_boxes", "Boxes beside the walkway", [(0, 200, 55, 80), (180, 390, 60, 75)], None),
        ("pinch", "Opposing obstacles", [(0, 210, 75, 100), (150, 210, 90, 100)], None),
        ("blocked", "Full-width obstruction", [(0, 270, 240, 70)], None),
        ("blur", "Out-of-focus capture", [(0, 210, 75, 100)], "blur"),
        ("glare", "Glare across the floor", [], "glare"),
        ("shifted", "Camera moved after reference", [(0, 210, 75, 100)], "shifted"),
        ("bad_geometry", "Floor too small in the frame", [], "geometry"),
        ("low_contrast", "Known limitation: low-contrast object", [(0, 210, 100, 100)], "low_contrast"),
    ]
    manifest = {"version": 1, "seed": 20261010, "kind": "owned synthetic planar fixtures", "fixtures": []}
    for name, title, rectangles, effect in scenarios:
        scene_floor = floor.copy()
        truth = np.zeros((600, 240), np.uint8)
        for x, y, w, h in rectangles:
            cv2.rectangle(scene_floor, (x, y), (x + w - 1, y + h - 1),
                          (130, 130, 130) if effect == "low_contrast" else (44, 77, 194), -1)
            cv2.rectangle(truth, (x, y), (x + w - 1, y + h - 1), 255, -1)
        scene = photograph(scene_floor)
        if effect == "blur":
            scene = cv2.GaussianBlur(scene, (41, 41), 10)
        elif effect == "glare":
            glare = scene_floor.copy()
            cv2.rectangle(glare, (20, 100), (220, 500), (255, 255, 255), -1)
            scene = photograph(glare)
        elif effect == "shifted":
            scene = cv2.warpAffine(scene, np.array([[1, 0, 38], [0, 1, 20]], np.float32), (900, 700))
        cal = {"points": corners.tolist(), "width_m": 2.4, "length_m": 6.0, "review_width_m": 1.2}
        if effect == "geometry":
            cal["points"] = [[400, 200], [450, 200], [450, 240], [400, 240]]
        # Independent known values come from generated rectangles, never the detector.
        widths = []
        for row in truth:
            free = np.pad(row == 0, (1, 1), constant_values=False)
            changes = np.diff(free.astype(np.int8))
            widths.append(max((b - a for a, b in zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1))), default=0))
        record = {"id": name, "title": title, "image": f"{name}.png", "reference": "reference.png",
                  "truth_mask": f"{name}.mask.png", "calibration": cal,
                  "expected": {"status": "needs_capture" if effect in {"blur", "glare", "shifted", "geometry"} else "review_required",
                               "clearance_m": round(min(widths) / 100, 2),
                               "changed_area_m2": round(np.count_nonzero(truth) / 10000, 4)},
                  "known_limitation": effect == "low_contrast"}
        cv2.imwrite(str(destination / record["image"]), scene)
        cv2.imwrite(str(destination / record["truth_mask"]), truth)
        manifest["fixtures"].append(record)
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_manifest() -> dict:
    if not (FIXTURES / "manifest.json").exists():
        return generate()
    return json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


def fixture_by_id(fixture_id: str) -> dict:
    fixture = next((item for item in load_manifest()["fixtures"] if item["id"] == fixture_id), None)
    if fixture is None:
        raise ValueError("Unknown fixture. Choose one from the fixture list.")
    return fixture
