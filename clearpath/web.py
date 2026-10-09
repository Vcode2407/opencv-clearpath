"""Local UI/API. Optional AWS container mode requires a bearer token for APIs."""
from __future__ import annotations

import hmac
import json
import os

import cv2
from flask import Flask, jsonify, request, send_from_directory

from .fixtures import FIXTURES, ROOT, fixture_by_id, load_manifest
from .vision import Calibration, decode_image, inspect, runtime_info


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=str(ROOT / "public"), static_url_path="/static")
    app.config.update(MAX_CONTENT_LENGTH=18_000_000, MODE=os.getenv("CLEARPATH_MODE", "local"),
                      API_TOKEN=os.getenv("CLEARPATH_API_TOKEN", ""))
    if config:
        app.config.update(config)
    if app.config["MODE"] not in {"local", "aws"}:
        raise ValueError("CLEARPATH_MODE must be local or aws.")
    if app.config["MODE"] == "aws" and len(app.config["API_TOKEN"]) < 24:
        raise ValueError("AWS mode requires CLEARPATH_API_TOKEN with at least 24 characters.")
    if app.config["MODE"] == "aws" and not runtime_info()["opencv5_verified"]:
        raise ValueError("The prepared competition container requires an actual OpenCV 5 runtime.")
    load_manifest()

    @app.before_request
    def protect_local_and_cloud():
        if app.config["MODE"] == "local" and not app.config.get("TESTING"):
            if request.host.split(":")[0] not in {"127.0.0.1", "localhost"}:
                return jsonify(error="Local mode accepts localhost requests only."), 403
            origin = request.headers.get("Origin")
            if origin and origin not in {f"http://{request.host}", f"https://{request.host}"}:
                return jsonify(error="Use the ClearPath page on this local origin."), 403
        if app.config["MODE"] == "aws" and request.path.startswith("/api/"):
            supplied = request.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied.encode("utf-8"), ("Bearer " + app.config["API_TOKEN"]).encode("utf-8")):
                return jsonify(error="Supply the deployment bearer token to access this API."), 401

    @app.after_request
    def secure_response(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        return send_from_directory(ROOT / "public", "index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok", **runtime_info(), mode=app.config["MODE"])

    @app.get("/api/fixtures")
    def fixtures():
        return jsonify(fixtures=load_manifest()["fixtures"])

    @app.get("/fixtures/<path:name>")
    def fixture_image(name):
        allowed = {item[key] for item in load_manifest()["fixtures"] for key in ("image", "reference")}
        if name not in allowed:
            return jsonify(error="Unknown fixture image."), 404
        return send_from_directory(FIXTURES, name)

    @app.post("/api/inspect")
    def analyze():
        try:
            if request.is_json:
                body = request.get_json()
                if not isinstance(body, dict) or not isinstance(body.get("fixture"), str):
                    raise ValueError("JSON inspection requires a fixture identifier.")
                fixture = fixture_by_id(body["fixture"])
                scene = cv2.imread(str(FIXTURES / fixture["image"]))
                reference = cv2.imread(str(FIXTURES / fixture["reference"]))
                raw = dict(fixture["calibration"])
                if "review_width_m" in body:
                    raw["review_width_m"] = body["review_width_m"]
            else:
                if not {"scene", "reference"}.issubset(request.files):
                    raise ValueError("Upload both a scene image and an aligned empty reference.")
                scene = decode_image(request.files["scene"].read(8_000_001))
                reference = decode_image(request.files["reference"].read(8_000_001))
                raw = json.loads(request.form.get("calibration", "{}"))
            if not isinstance(raw, dict):
                raise ValueError("Calibration must be a JSON object.")
            report, _ = inspect(scene, reference, Calibration.from_dict(raw))
            report["source"] = fixture["title"] if request.is_json else "Uploaded image pair"
            return jsonify(report)
        except (ValueError, TypeError, json.JSONDecodeError, cv2.error) as exc:
            return jsonify(error=str(exc)), 400

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error="The upload exceeds 18 MB. Use two images smaller than 8 MB each."), 413

    return app


app = create_app()
