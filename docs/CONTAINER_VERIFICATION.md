# Local Linux container verification

Recorded October 10, 2026, at approximately 23:04 IST. **The existing Dockerfile now builds and runs successfully on the local Docker Desktop Linux engine.** This is local container verification, not AWS deployment or competition qualification.

No AWS account, API, deployment, billing, or cloud resources were used. No software was installed on the host, agreement was accepted, or OS security setting was changed. Docker Desktop was already installed and was started with its official CLI. The container build downloaded its existing pinned Python dependencies into the image.

## Docker Desktop startup

Before startup, `docker version` reported client 29.8.1, context `desktop-linux`, and failed to connect to `npipe:////./pipe/dockerDesktopLinuxEngine` because the pipe did not exist. `docker desktop status` returned:

```text
Could not retrieve status. Is Docker Desktop running?
You can start Docker Desktop by running 'docker desktop start'.
```

The installed CLI help exposed `--detach` and `--timeout seconds`. The following actual command completed with exit code 0 and `✓ Starting Docker Desktop`:

```powershell
docker desktop start --detach --timeout 30
```

The subsequent status was `running`. The responding server reported Docker Desktop **4.93.0 (240920)**, Engine **29.8.1**, API **1.56**, and **linux/amd64**. The Desktop CLI plugin reported **v0.4.4**. No desktop application was manually launched with a visible window.

## Actual build and run

From the ClearPath repository root:

```powershell
docker build --progress plain -t clearpath:local-verify-20261010 .
$env:CLEARPATH_API_TOKEN = 'local-only-clearpath-verification-20261010'
docker run --detach --rm --name clearpath-local-verify-20261010 --publish 127.0.0.1:4191:4181 --env CLEARPATH_API_TOKEN clearpath:local-verify-20261010
Remove-Item Env:\CLEARPATH_API_TOKEN
```

The literal token above is a disposable local verification value, not an account credential or production secret. Port 4191 had no listener before this run. No application source or Dockerfile was changed for the verification.

The build completed with exit code 0. Build output resolved the base image to:

```text
python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
```

The resulting local image ID reported by `docker image inspect` was:

```text
sha256:b3e5c0767ed861bbdcb65cf7d7eb78bf0c7e8d0214fbfa32c0054834c1808248
```

The image reports `linux/amd64` and configured user `clearpath`. The actual container ID was `8b3fd94d7a8bda1fd451aa98185ca1a5b7e08252f9ebd6635f6d12d587ee9432`. Its inspected host-port mapping was only:

```json
{"4181/tcp":[{"HostIp":"127.0.0.1","HostPort":"4191"}]}
```

Gunicorn logs showed version 23.0.0 starting, listening on `0.0.0.0:4181` **inside the container**, using `gthread`, and booting its worker. The host exposure remains the loopback mapping above.

## Observed runtime and API results

The following probes were made against `http://127.0.0.1:4191` using PowerShell `Invoke-WebRequest -UseBasicParsing`. Successful inspection responses were parsed as JSON; image payloads were not printed or saved to the host.

| Probe | Observed result |
| --- | --- |
| `GET /health`, no bearer token | HTTP 200 with the exact runtime shown below. |
| `GET /api/fixtures`, missing token | HTTP 401: `Supply the deployment bearer token to access this API.` |
| `GET /api/fixtures`, deliberately wrong bearer token | HTTP 401 with the same error. |
| `GET /api/fixtures`, correct local dummy bearer token | HTTP 200; nine fixtures. |
| `POST /api/inspect`, correct token, `{"fixture":"pinch","review_width_m":1.2}` | HTTP 200; source `Opposing obstacles`; `review_required`; 0.75 m projected cross-section and 1.65 m² changed area. |
| Inspection response headers | `Cache-Control: no-store`; `X-Content-Type-Options: nosniff`. |
| `docker exec ... python --version` | Python 3.12.10. |
| `docker exec ... python -m clearpath runtime` | OpenCV 5.0.0 verified, CPU, no AI provider, AWS verification false. |
| `docker exec ... python -m pip show opencv-python-headless gunicorn` | OpenCV wheel 5.0.0.93; Gunicorn 23.0.0. |
| `docker exec ... python -m pip check` | Exit code 0; `No broken requirements found.` |
| `docker exec ... id` | `uid=10001(clearpath) gid=10001(clearpath) groups=10001(clearpath)`. |

Actual health JSON:

```json
{
  "ai_provider": "none",
  "aws_deployment_verified": false,
  "compute": "CPU",
  "mode": "aws",
  "opencv5_verified": true,
  "opencv_version": "5.0.0",
  "status": "ok"
}
```

`mode: "aws"` selects the prepared bearer-protected configuration from the Dockerfile. It does not establish an AWS execution location; `aws_deployment_verified` correctly remains `false`.

The pinch inspection also reported two changed regions, a bottleneck row at 2.1 m, `point_route_exists: true`, and `below_review_target: true` for the 1.2 m target. Geometry and capture quality were accepted; the trace then recorded floor projection, changed-region measurement, and a request for human review. The response contained PNG data URLs for `annotated_image`, `occupancy_image`, and `rectified_image`.

This one fixture confirms actual server-side OpenCV processing in the Linux container. It does not establish field accuracy, body-width traversal, safety, accessibility compliance, or a complete container regression evaluation. The existing nine-fixture synthetic evaluation, including its low-contrast failure, remains documented in [REPORT.md](REPORT.md).

## Build inputs recorded

SHA-256 values at verification time:

| File | SHA-256 |
| --- | --- |
| `Dockerfile` | `d40c07677253a0b9e53e35db5c141fb9e9caa0de4ec5fbfc323a19a1b28d6505` |
| `requirements.txt` | `f32844db6ac8517ecb83e466621c1aa0b81b2fd3edd68583a40c4fb23c363f2d` |
| `requirements-cloud.txt` | `2673161451f5df48988b86ee84ba6d8642d90beab8ba3cf0021c4c8d52dd9d89` |

## Retained resources and remaining gates

The named container is left running for local review at port 4191, and Docker Desktop remains running. The local image is retained. To stop and automatically remove this verification container:

```powershell
docker stop clearpath-local-verify-20261010
```

No AWS deployment, ECR push, CloudFormation validation, ECS service, remote endpoint, ARM/Graviton run, or physical-image evaluation was performed. Actual AWS processing, judge access, and the organizer's proposal/registration gate remain pending. The README, AWS preparation, technical report and submission draft reflect this local validation.
