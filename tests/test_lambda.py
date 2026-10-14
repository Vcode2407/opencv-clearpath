import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from types import SimpleNamespace

import cv2
import pytest

from clearpath.fixtures import FIXTURES, fixture_by_id
from clearpath.lambda_evidence import run
from clearpath.lambda_runtime import MAX_EVENT_BYTES, MAX_IMAGE_BYTES, handler

FUNCTION = "arn:aws:lambda:ap-south-1:123456789012:function:clearpath-inspect"
IMAGE = "123456789012.dkr.ecr.ap-south-1.amazonaws.com/clearpath@sha256:" + "a" * 64
REQUEST_ID = "12345678-1234-1234-1234-123456789abc"


def test_lambda_fixture_runs_real_vision_without_claiming_cloud_execution():
    result = handler({"fixture": "pinch"})
    assert result["report"]["measurements"]["clearance_m"] == pytest.approx(0.75, abs=0.04)
    assert result["report"]["measurements"]["changed_area_m2"] == pytest.approx(1.65, abs=0.06)
    assert result["report"]["runtime"]["opencv_version"].startswith("5.")
    assert result["report"]["runtime"]["aws_deployment_verified"] is False
    assert result["execution"]["aws_execution_verified"] is False
    assert result["execution"]["context_observed"] is False
    assert not any(key.endswith("_image") for key in result["report"])
    assert "data:image" not in json.dumps(result)


def test_lambda_owned_aligned_pair_preserves_real_measurements():
    fixture = fixture_by_id("edge_boxes")
    event = {"scene_base64": base64.b64encode((FIXTURES / fixture["image"]).read_bytes()).decode(),
             "reference_base64": base64.b64encode((FIXTURES / fixture["reference"]).read_bytes()).decode(),
             "calibration": fixture["calibration"]}
    result = handler(event)
    assert result["report"]["measurements"]["clearance_m"] == pytest.approx(1.8, abs=0.04)
    assert result["report"]["source"] == "Supplied aligned image pair"


@pytest.mark.parametrize("fixture", ["blur", "glare", "shifted"])
def test_lambda_quality_failures_withhold_measurements(fixture):
    result = handler({"fixture": fixture})
    assert result["report"]["status"] == "needs_capture"
    assert result["report"]["measurements"] is None
    assert result["report"]["capture_requests"]


def test_lambda_preserves_known_low_contrast_false_negative():
    result = handler({"fixture": "low_contrast"})
    expected = fixture_by_id("low_contrast")["expected"]["clearance_m"]
    assert result["report"]["measurements"]["clearance_m"] - expected == pytest.approx(1.0)
    assert any("Low-contrast" in limit for limit in result["report"]["limitations"])


def test_lambda_rejects_image_pixel_bomb_before_opencv_allocation(monkeypatch):
    called = []
    monkeypatch.setattr(cv2, "imdecode", lambda *args: called.append(args))
    header = b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", 4000, 3000)
    event = {"scene_base64": base64.b64encode(header).decode(),
             "reference_base64": base64.b64encode(header).decode(),
             "calibration": fixture_by_id("clear")["calibration"]}
    with pytest.raises(ValueError, match="8 megapixels"):
        handler(event)
    assert called == []


def test_lambda_payload_cap_precedes_vision_and_disallows_url_inputs(monkeypatch):
    called = []
    monkeypatch.setattr(cv2, "imdecode", lambda *args: called.append(args))
    with pytest.raises(ValueError, match="5.6 MB"):
        handler({"scene_base64": "a" * MAX_EVENT_BYTES})
    with pytest.raises(ValueError, match="require scene_base64"):
        handler({"scene_url": "https://example.invalid/image.png"})
    assert called == []


@pytest.mark.parametrize("encoded", ["data:image/png;base64,AAAA", "!!!!", "", None])
def test_lambda_invalid_base64_never_reaches_image_decode(monkeypatch, encoded):
    called = []
    monkeypatch.setattr(cv2, "imdecode", lambda *args: called.append(args))
    event = {"scene_base64": encoded, "reference_base64": encoded,
             "calibration": fixture_by_id("clear")["calibration"]}
    with pytest.raises(ValueError, match="base64"):
        handler(event)
    assert called == []


def test_lambda_decoded_image_byte_cap_precedes_opencv(monkeypatch):
    called = []
    monkeypatch.setattr(cv2, "imdecode", lambda *args: called.append(args))
    encoded = base64.b64encode(b"a" * (MAX_IMAGE_BYTES + 1)).decode()
    event = {"scene_base64": encoded, "reference_base64": encoded,
             "calibration": fixture_by_id("clear")["calibration"]}
    with pytest.raises(ValueError, match="2 MB"):
        handler(event)
    assert called == []


@pytest.mark.parametrize("event", [{"fixture": "pinch", "scene_url": "https://example.invalid/"},
                                  {"fixture": "pinch", "review_width_m": float("nan")},
                                  {"fixture": "../manifest.json"}])
def test_lambda_invalid_fixture_event_is_refused(event):
    with pytest.raises(ValueError):
        handler(event)


def arguments(tmp_path, execute=True):
    event = tmp_path / "event.json"
    event.write_text('{"fixture":"pinch"}', encoding="utf-8")
    return argparse.Namespace(function_arn=FUNCTION, image_uri=IMAGE, version="1", region="ap-south-1",
                              profile="owner-test-profile", event=event, output=tmp_path / "evidence",
                              execute_one_call=execute)


def fake_config():
    return {"FunctionArn": FUNCTION + ":1", "Version": "1", "State": "Active",
            "LastUpdateStatus": "Successful", "Architectures": ["x86_64"],
            "MemorySize": 2048, "Timeout": 60, "ImageUri": IMAGE}


def fake_transport(calls, bad_receipt=False, timeout=False, mutate=None):
    def call(command, **kwargs):
        calls.append((command, kwargs))
        assert kwargs["env"]["AWS_MAX_ATTEMPTS"] == "1"
        assert kwargs["env"]["AWS_RETRY_MODE"] == "standard"
        assert command[command.index("--endpoint-url") + 1] == "https://lambda.ap-south-1.amazonaws.com"
        assert "--no-verify-ssl" not in command
        if "get-function" in command:
            return SimpleNamespace(returncode=0, stdout=json.dumps(fake_config()))
        assert command.count("invoke") == 1
        if timeout:
            raise subprocess.TimeoutExpired(command, 100)
        context = SimpleNamespace(invoked_function_arn=FUNCTION + ":1", function_version="1", aws_request_id=REQUEST_ID)
        result = handler({"fixture": "pinch"}, context)
        if bad_receipt:
            result["execution"]["request_sha256"] = "b" * 64
        tail = f"START RequestId: {REQUEST_ID} Version: 1\nEND RequestId: {REQUEST_ID}\nREPORT RequestId: {REQUEST_ID}\tDuration: 25 ms\tBilled Duration: 26 ms\tMemory Size: 2048 MB\tMax Memory Used: 120 MB\n"
        metadata = {"StatusCode": 200, "ExecutedVersion": "1", "LogResult": base64.b64encode(tail.encode()).decode()}
        if mutate:
            mutate(result, metadata)
        Path(command[command.index("--output") - 1]).write_text(json.dumps(result), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout=json.dumps(metadata))
    return call


def test_lambda_preparation_performs_no_cloud_calls(tmp_path):
    calls = []
    result = run(arguments(tmp_path, execute=False), fake_transport(calls))
    assert calls == []
    assert result["outcome"] == "prepared_only"
    assert result["awsExecutionVerified"] is False
    assert result["invocationAttempted"] is False


def test_lambda_evidence_correlates_one_transport_call_and_preserves_runtime_qualification(tmp_path):
    calls = []
    args = arguments(tmp_path)
    result = run(args, fake_transport(calls))
    assert len(calls) == 2  # One metadata read plus exactly one injected invocation.
    assert result["outcome"] == "verified_synchronous_execution"
    assert result["requestId"] == REQUEST_ID
    assert result["runtime"]["aws_deployment_verified"] is False
    assert result["responseSha256"] == hashlib.sha256((args.output / "response.json").read_bytes()).hexdigest()
    # This is injected transport evidence in a temporary test directory, not AWS.
    assert json.loads((args.output / "invoke-metadata.json").read_text())["ExecutedVersion"] == "1"


def test_lambda_unknown_invocation_is_retained_without_retry(tmp_path):
    calls = []
    args = arguments(tmp_path)
    with pytest.raises(subprocess.TimeoutExpired):
        run(args, fake_transport(calls, timeout=True))
    assert len(calls) == 2
    saved = json.loads((args.output / "evidence.json").read_text())
    assert saved["invocationAttempted"] is True
    assert saved["awsExecutionVerified"] is False
    assert saved["outcome"] == "unknown_or_unverified"


def test_lambda_mismatching_configuration_stops_before_invocation(tmp_path):
    calls = []
    def call(command, **kwargs):
        calls.append(command)
        wrong = {**fake_config(), "ImageUri": IMAGE[:-1] + "b"}
        return SimpleNamespace(returncode=0, stdout=json.dumps(wrong))
    args = arguments(tmp_path)
    with pytest.raises(ValueError, match="differs from the reviewed plan"):
        run(args, call)
    assert len(calls) == 1
    assert json.loads((args.output / "evidence.json").read_text())["outcome"] == "preflight_failed"


def test_lambda_mismatching_receipt_cannot_be_claimed_verified(tmp_path):
    calls = []
    args = arguments(tmp_path)
    with pytest.raises(ValueError, match="receipt does not match"):
        run(args, fake_transport(calls, bad_receipt=True))
    assert len(calls) == 2
    assert json.loads((args.output / "evidence.json").read_text())["awsExecutionVerified"] is False


@pytest.mark.parametrize("field,value", [("vision_source_sha256", "b" * 64),
                                        ("vision_source_hash_normalization", "raw_bytes"),
                                        ("function_arn", FUNCTION + ":2"),
                                        ("function_version", "$LATEST"),
                                        ("context_observed", False)])
def test_lambda_foreign_execution_receipt_is_unverified(tmp_path, field, value):
    calls = []
    args = arguments(tmp_path)
    def mutate(result, metadata):
        result["execution"][field] = value
    with pytest.raises(ValueError, match="receipt does not match"):
        run(args, fake_transport(calls, mutate=mutate))
    assert len(calls) == 2
    assert json.loads((args.output / "evidence.json").read_text())["awsExecutionVerified"] is False


@pytest.mark.parametrize("field,value", [("StatusCode", 202), ("ExecutedVersion", "2"),
                                        ("FunctionError", "Unhandled"), ("LogResult", "invalid!")])
def test_lambda_missing_platform_evidence_stays_unverified(tmp_path, field, value):
    calls = []
    args = arguments(tmp_path)
    def mutate(result, metadata):
        metadata[field] = value
    with pytest.raises(ValueError):
        run(args, fake_transport(calls, mutate=mutate))
    assert len(calls) == 2
    assert json.loads((args.output / "evidence.json").read_text())["awsExecutionVerified"] is False


@pytest.mark.parametrize("field,value", [("version", "$LATEST"), ("region", "us-east-1"),
                                        ("image_uri", IMAGE.replace("123456789012", "111111111111")),
                                        ("image_uri", IMAGE.split("@")[0] + ":latest")])
def test_lambda_unreviewed_target_is_rejected_before_transport(tmp_path, field, value):
    calls = []
    args = arguments(tmp_path)
    setattr(args, field, value)
    with pytest.raises(ValueError):
        run(args, fake_transport(calls))
    assert calls == []
    assert not args.output.exists()


def test_lambda_evidence_refuses_to_overwrite_a_previous_attempt(tmp_path):
    calls = []
    args = arguments(tmp_path, execute=False)
    run(args, fake_transport(calls))
    with pytest.raises(FileExistsError):
        run(args, fake_transport(calls))
    assert calls == []
