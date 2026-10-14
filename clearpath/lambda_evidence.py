"""Prepare a private Lambda plan, or perform one explicitly requested owner invocation.

There are no cloud calls unless --execute-one-call is supplied. CLI retries are
disabled. An uncertain invocation is recorded and is never automatically repeated.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Callable

from .lambda_runtime import MAX_EVENT_BYTES, MAX_RESPONSE_BYTES, event_bytes, input_images, vision_source_hash

ARN = re.compile(r"arn:aws:lambda:([a-z0-9-]+):([0-9]{12}):function:([a-zA-Z0-9_-]{1,64})\Z")
IMAGE = re.compile(r"([0-9]{12})\.dkr\.ecr\.([a-z0-9-]+)\.amazonaws\.com/[a-z0-9./_-]+@sha256:[a-f0-9]{64}\Z")
UUID = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
REGION = re.compile(r"[a-z]{2}-[a-z]+-[1-9][0-9]*\Z")


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _record(path: Path, value: dict):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _check_config(configuration: dict, plan: dict):
    if not isinstance(configuration, dict):
        raise ValueError("The function configuration response is not a JSON object.")
    target = plan["functionArn"]
    version = plan["version"]
    expected = {
        "Version": version, "State": "Active", "LastUpdateStatus": "Successful",
        "Architectures": ["x86_64"], "MemorySize": 2048, "Timeout": 60,
        "ImageUri": plan["imageUri"],
    }
    if configuration.get("FunctionArn") not in {target, target + ":" + version}:
        raise ValueError("The configured function ARN differs from the reviewed target.")
    if any(configuration.get(key) != value for key, value in expected.items()):
        raise ValueError("The active immutable function configuration differs from the reviewed plan.")


def _check_result(result: dict, metadata: dict, plan: dict) -> dict:
    if not isinstance(result, dict) or not isinstance(metadata, dict):
        raise ValueError("The invocation result and metadata must be JSON objects.")
    if metadata.get("StatusCode") != 200 or metadata.get("FunctionError") or metadata.get("ExecutedVersion") != plan["version"]:
        raise ValueError("Invoke did not return a successful result from the reviewed version.")
    execution = result.get("execution", {})
    report = result.get("report", {})
    if not isinstance(execution, dict) or not isinstance(report, dict):
        raise ValueError("The response is missing its report or execution receipt.")
    request_id = execution.get("request_id", "")
    if not isinstance(request_id, str) or not re.fullmatch(UUID, request_id):
        raise ValueError("The response is missing a valid execution request identifier.")
    expected = {
        "schema": "clearpath.lambda.v1", "request_sha256": plan["requestSha256"],
        "function_arn": plan["functionArn"] + ":" + plan["version"],
        "function_version": plan["version"], "context_observed": True,
        "aws_execution_verified": False,
        "vision_source_sha256": plan["visionSourceSha256"],
        "vision_source_hash_normalization": "crlf_to_lf",
    }
    if any(execution.get(key) != value for key, value in expected.items()):
        raise ValueError("The response receipt does not match this invocation plan.")
    runtime = report.get("runtime", {})
    if not isinstance(runtime, dict):
        raise ValueError("The runtime evidence must be a JSON object.")
    if runtime.get("opencv5_verified") is not True or runtime.get("compute") != "CPU" or runtime.get("aws_deployment_verified") is not False:
        raise ValueError("The response is missing qualified actual CPU OpenCV 5 runtime evidence.")
    if report.get("status") not in {"review_required", "needs_capture"} or report.get("image_evidence_omitted") is not True:
        raise ValueError("The response is not a compact inspection report.")
    source_hash = execution.get("vision_source_sha256", "")
    if not isinstance(source_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", source_hash):
        raise ValueError("The response is missing its vision source hash.")
    try:
        logs = base64.b64decode(metadata.get("LogResult", ""), validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("The invocation log tail is invalid.") from exc
    # Only retain fixed platform lines; image bytes and arbitrary log messages stay out.
    lines = [line for line in logs.splitlines() if any(line.startswith(prefix + request_id) for prefix in ("START RequestId: ", "END RequestId: ", "REPORT RequestId: "))]
    if len(lines) != 3 or any(sum(line.startswith(prefix + request_id) for line in lines) != 1 for prefix in ("START RequestId: ", "END RequestId: ", "REPORT RequestId: ")):
        raise ValueError("The log tail does not contain matching START, END and REPORT evidence.")
    if not any(re.search(r"Version: " + re.escape(plan["version"]) + r"(?:\s|$)", line) for line in lines):
        raise ValueError("The execution log does not confirm the reviewed version.")
    return {"requestId": request_id, "platformLogLines": lines,
            "visionSourceSha256": execution["vision_source_sha256"],
            "status": report["status"], "measurements": report.get("measurements"),
            "captureRequests": report.get("capture_requests", []), "runtime": runtime}


def run(args: argparse.Namespace, call: Callable = subprocess.run) -> dict:
    function = ARN.fullmatch(args.function_arn)
    image = IMAGE.fullmatch(args.image_uri)
    if not REGION.fullmatch(args.region) or not function or not image or function.group(1) != args.region or image.group(2) != args.region or image.group(1) != function.group(2):
        raise ValueError("Use the reviewed same-account, same-region function ARN and ECR digest.")
    if not re.fullmatch(r"[1-9][0-9]*", args.version) or not args.profile.strip():
        raise ValueError("Supply a positive immutable version number and an owner-configured CLI profile.")
    if args.event.stat().st_size > MAX_EVENT_BYTES:
        raise ValueError("The event exceeds 5.6 MB.")
    event = _json(args.event)
    payload = event_bytes(event)
    input_images(event)  # Reject invalid schema/image dimensions before any AWS call.
    args.output.mkdir(parents=True, exist_ok=False)
    plan = {"preparedAtUtc": datetime.now(timezone.utc).isoformat(),
            "functionArn": args.function_arn, "version": args.version, "imageUri": args.image_uri,
            "region": args.region, "requestSha256": hashlib.sha256(payload).hexdigest(),
            "visionSourceSha256": vision_source_hash(), "visionSourceHashNormalization": "crlf_to_lf",
            "invocationType": "RequestResponse", "maxAttempts": 1,
            "cloudCallsAuthorizedByFlag": args.execute_one_call, "invocationAttempted": False,
            "awsExecutionVerified": False, "outcome": "prepared_only"}
    _record(args.output / "evidence.json", plan)
    if not args.execute_one_call:
        return plan
    environment = dict(os.environ, AWS_MAX_ATTEMPTS="1", AWS_RETRY_MODE="standard", AWS_PAGER="")
    # Prevent an environment/profile endpoint override from turning local emulation
    # into an apparent AWS receipt. TLS certificate verification remains enabled.
    base = ["aws", "--profile", args.profile, "--region", args.region, "--no-cli-pager", "--no-cli-auto-prompt",
            "--endpoint-url", "https://lambda." + args.region + ".amazonaws.com",
            "--cli-connect-timeout", "10", "--cli-read-timeout", "75"]
    def aws(arguments: list[str], timeout: int):
        completed = call(base + arguments, env=environment, capture_output=True, text=True, timeout=timeout)
        if completed.returncode:
            raise RuntimeError("AWS CLI returned an error; review account status directly. No automatic retry.")
        return json.loads(completed.stdout)
    try:
        configuration = aws(["lambda", "get-function", "--function-name", args.function_arn, "--qualifier", args.version,
                             "--query", "{FunctionArn:Configuration.FunctionArn,Version:Configuration.Version,State:Configuration.State,LastUpdateStatus:Configuration.LastUpdateStatus,Architectures:Configuration.Architectures,MemorySize:Configuration.MemorySize,Timeout:Configuration.Timeout,ImageUri:Code.ResolvedImageUri}", "--output", "json"], 40)
        _check_config(configuration, plan)
        _record(args.output / "function-configuration.json", configuration)
        request_path = (args.output / "request.json").resolve()
        response_path = (args.output / "response.json").resolve()
        request_path.write_bytes(payload)
        plan.update(invocationAttempted=True, outcome="unknown")
        _record(args.output / "evidence.json", plan)  # Persist before the one chargeable call.
        metadata = aws(["lambda", "invoke", "--function-name", args.function_arn, "--qualifier", args.version,
                        "--invocation-type", "RequestResponse", "--log-type", "Tail", "--cli-binary-format", "raw-in-base64-out",
                        "--payload", "fileb://" + str(request_path), str(response_path), "--output", "json"], 100)
        _record(args.output / "invoke-metadata.json", {key: metadata.get(key) for key in ("StatusCode", "ExecutedVersion", "FunctionError")})
        if response_path.stat().st_size > MAX_RESPONSE_BYTES:
            raise ValueError("The invocation response exceeds the adapter's 500 KB limit.")
        facts = _check_result(_json(response_path), metadata, plan)
        plan.update(facts, awsExecutionVerified=True, outcome="verified_synchronous_execution",
                    observedAtUtc=datetime.now(timezone.utc).isoformat(),
                    responseSha256=hashlib.sha256(response_path.read_bytes()).hexdigest())
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        plan["outcome"] = "unknown_or_unverified" if plan["invocationAttempted"] else "preflight_failed"
        plan["failureType"] = type(exc).__name__
        _record(args.output / "evidence.json", plan)
        raise
    _record(args.output / "evidence.json", plan)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--function-arn", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--image-uri", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New evidence directory; existing directories are refused. Keep it ignored/private.")
    parser.add_argument("--execute-one-call", action="store_true", help="Owner-reviewed permission to read configuration and invoke once; can incur charges.")
    args = parser.parse_args()
    plan = run(args)
    print(json.dumps({key: plan[key] for key in ("outcome", "invocationAttempted", "awsExecutionVerified")}, indent=2))


if __name__ == "__main__":
    main()
