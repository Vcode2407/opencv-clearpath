import io
import json

import pytest

from clearpath.fixtures import FIXTURES, fixture_by_id
from clearpath.web import create_app


@pytest.fixture
def client():
    return create_app({"TESTING": True}).test_client()


def test_browser_shell_and_runtime_endpoint(client):
    assert client.get("/").status_code == 200
    health = client.get("/health").json
    assert health["opencv_version"].startswith("5.")
    assert health["aws_deployment_verified"] is False
    assert client.get("/static/app.js").status_code == 200


def test_fixture_api_runs_real_inspection_and_quality_gate(client):
    response = client.post("/api/inspect", json={"fixture": "pinch"})
    assert response.status_code == 200
    assert response.json["measurements"]["clearance_m"] == pytest.approx(0.75, abs=0.04)
    assert client.post("/api/inspect", json={"fixture": "blur"}).json["measurements"] is None


def test_registered_image_pair_upload_is_analyzed(client):
    fixture = fixture_by_id("edge_boxes")
    response = client.post("/api/inspect", data={
        "scene": (io.BytesIO((FIXTURES / fixture["image"]).read_bytes()), "scene.png"),
        "reference": (io.BytesIO((FIXTURES / fixture["reference"]).read_bytes()), "reference.png"),
        "calibration": json.dumps(fixture["calibration"]),
    })
    assert response.status_code == 200
    assert response.json["measurements"]["clearance_m"] == pytest.approx(1.8, abs=0.04)


@pytest.mark.parametrize("body", [{"fixture": "../README.md"}, {"fixture": "clear", "review_width_m": "bad"}, [], {}])
def test_bad_inputs_are_actionable_json_errors(client, body):
    response = client.post("/api/inspect", json=body)
    assert response.status_code == 400
    assert response.json["error"]


def test_fixture_files_are_whitelisted(client):
    assert client.get("/fixtures/manifest.json").status_code == 404
    assert client.get("/fixtures/../README.md").status_code == 404


def test_cloud_mode_requires_secret_and_protects_api():
    with pytest.raises(ValueError, match="local or aws"):
        create_app({"MODE": "typo"})
    with pytest.raises(ValueError, match="24 characters"):
        create_app({"MODE": "aws", "API_TOKEN": "short"})
    token = "this-is-a-test-token-at-least-24-chars"
    cloud = create_app({"TESTING": True, "MODE": "aws", "API_TOKEN": token}).test_client()
    assert cloud.get("/health").status_code == 200
    assert cloud.get("/api/fixtures").status_code == 401
    assert cloud.get("/api/fixtures", headers={"Authorization": "Bearer café"}).status_code == 401
    assert cloud.post("/api/inspect", json={"fixture": "clear"}).status_code == 401
    assert cloud.post("/api/inspect", json={"fixture": "clear"}, headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_local_mode_rejects_cross_origin_and_unknown_hosts():
    local = create_app().test_client()
    assert local.get("/health", base_url="http://attacker.example").status_code == 403
    assert local.post("/api/inspect", json={"fixture": "clear"}, base_url="http://127.0.0.1:4181", headers={"Origin": "http://attacker.example"}).status_code == 403
