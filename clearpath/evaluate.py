"""Independent mask/measurement comparison against generated fixture labels."""
import json
from pathlib import Path

import cv2
import numpy as np

from .fixtures import FIXTURES, ROOT, load_manifest
from .vision import Calibration, inspect, runtime_info


def evaluate(output: Path | None = None) -> dict:
    rows = []
    for fixture in load_manifest()["fixtures"]:
        scene = cv2.imread(str(FIXTURES / fixture["image"]))
        reference = cv2.imread(str(FIXTURES / fixture["reference"]))
        report, predicted = inspect(scene, reference, Calibration.from_dict(fixture["calibration"]))
        row = {"fixture": fixture["id"], "expected_status": fixture["expected"]["status"],
               "actual_status": report["status"], "status_correct": report["status"] == fixture["expected"]["status"],
               "known_limitation": fixture["known_limitation"], "capture_requests": report["capture_requests"]}
        if predicted is not None:
            truth = cv2.imread(str(FIXTURES / fixture["truth_mask"]), cv2.IMREAD_GRAYSCALE) > 0
            detected = predicted > 0
            union = int(np.count_nonzero(truth | detected))
            intersection = int(np.count_nonzero(truth & detected))
            row["mask_iou"] = round(intersection / union, 4) if union else 1.0
            row["clearance_truth_m"] = fixture["expected"]["clearance_m"]
            row["clearance_measured_m"] = report["measurements"]["clearance_m"]
            row["clearance_abs_error_m"] = round(abs(row["clearance_truth_m"] - row["clearance_measured_m"]), 4)
            row["area_truth_m2"] = fixture["expected"]["changed_area_m2"]
            row["area_measured_m2"] = report["measurements"]["changed_area_m2"]
        rows.append(row)
    baseline = [row for row in rows if "mask_iou" in row and not row["known_limitation"]]
    result = {"runtime": runtime_info(), "dataset": "9 deterministic owned planar fixtures; not real-world validation",
              "summary": {"status_correct": sum(row["status_correct"] for row in rows), "total": len(rows),
                          "baseline_mean_iou": round(float(np.mean([row["mask_iou"] for row in baseline])), 4),
                          "baseline_mean_clearance_error_m": round(float(np.mean([row["clearance_abs_error_m"] for row in baseline])), 4)},
              "cases": rows}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
