"""Private synchronous Lambda adapter; the vision pipeline is shared unchanged.

An execution context is reported as data, never used as proof of AWS deployment.
The caller must retain the real Invoke metadata, immutable image and platform logs.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
from pathlib import Path
from typing import Any

import cv2

from . import vision
from .fixtures import FIXTURES, fixture_by_id
from .vision import Calibration, decode_image, inspect, runtime_info

MAX_EVENT_BYTES = 5_600_000
MAX_IMAGE_BYTES = 2_000_000
MAX_RESPONSE_BYTES = 500_000
IMAGE_FIELDS = {"annotated_image", "rectified_image", "occupancy_image"}


def vision_source_hash() -> str:
    """Hash the vision source with CRLF normalized to LF on either build host."""
    source = Path(vision.__file__).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(source).hexdigest()


def event_bytes(event: Any) -> bytes:
    if not isinstance(event, dict):
        raise ValueError("Supply a JSON object with a fixture or an aligned image pair.")
    try:
        body = json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError("Supply finite JSON values in the inspection event.") from exc
    if len(body) > MAX_EVENT_BYTES:
        raise ValueError("The synchronous inspection event exceeds 5.6 MB.")
    return body


def _image(encoded: Any):
    if not isinstance(encoded, str) or not encoded or len(encoded) > 4 * ((MAX_IMAGE_BYTES + 2) // 3):
        raise ValueError("Each image must be plain base64 for a PNG/JPEG no larger than 2 MB.")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Each image must use valid plain base64, without a data URL.") from exc
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Each decoded image must be no larger than 2 MB.")
    return decode_image(data)


def input_images(event: dict):
    """Validate the private invocation schema without URLs, file paths or uploads."""
    if "fixture" in event:
        if set(event) - {"fixture", "review_width_m"} or not isinstance(event["fixture"], str):
            raise ValueError("Fixture events accept only fixture and optional review_width_m.")
        if not (FIXTURES / "manifest.json").is_file():
            raise ValueError("The container is missing its packaged fixture manifest.")
        fixture = fixture_by_id(event["fixture"])
        calibration = dict(fixture["calibration"])
        if "review_width_m" in event:
            calibration["review_width_m"] = event["review_width_m"]
        scene = decode_image((FIXTURES / fixture["image"]).read_bytes())
        reference = decode_image((FIXTURES / fixture["reference"]).read_bytes())
        return scene, reference, Calibration.from_dict(calibration), fixture["title"]
    if set(event) != {"scene_base64", "reference_base64", "calibration"}:
        raise ValueError("Image-pair events require scene_base64, reference_base64 and calibration only.")
    if not isinstance(event["calibration"], dict):
        raise ValueError("Calibration must be a JSON object.")
    return (_image(event["scene_base64"]), _image(event["reference_base64"]),
            Calibration.from_dict(event["calibration"]), "Supplied aligned image pair")


def handler(event: Any, context: Any = None) -> dict:
    """Run actual CPU OpenCV inspection and return bounded JSON without image data."""
    body = event_bytes(event)
    if not runtime_info()["opencv5_verified"]:
        raise ValueError("This container requires an actual OpenCV 5 runtime.")
    scene, reference, calibration, source = input_images(event)
    # One invocation performs one inspection. No network, credentials or file writes.
    cv2.setNumThreads(1)
    report, _ = inspect(scene, reference, calibration)
    compact = {key: value for key, value in report.items() if key not in IMAGE_FIELDS}
    compact["source"] = source
    compact["image_evidence_omitted"] = True
    # The receipt does not replace the original local overlay or a human's review.
    receipt = {
        "schema": "clearpath.lambda.v1",
        "request_sha256": hashlib.sha256(body).hexdigest(),
        "vision_source_sha256": vision_source_hash(),
        "vision_source_hash_normalization": "crlf_to_lf",
        "context_observed": context is not None,
        "function_arn": getattr(context, "invoked_function_arn", None),
        "function_version": getattr(context, "function_version", None),
        "request_id": getattr(context, "aws_request_id", None),
        "aws_execution_verified": False,
    }
    response = {"report": compact, "execution": receipt}
    if len(json.dumps(response, separators=(",", ":"), allow_nan=False).encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise ValueError("The JSON evidence exceeds 500 KB; use a smaller inspection region.")
    return response
