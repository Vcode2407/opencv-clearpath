# ClearPath

ClearPath measures projected changes in a controlled walkway using an aligned empty reference, four measured floor corners, and **real CPU OpenCV 5**. The browser shows the region overlay, the narrowest widest free cross-section, capture problems, and the evidence to review.

Public MIT source: [Vcode2407/opencv-clearpath](https://github.com/Vcode2407/opencv-clearpath). [Automated checks](https://github.com/Vcode2407/opencv-clearpath/actions) exercise vision/API tests on Windows and Ubuntu, save the synthetic evaluation, and build a non-root Linux container. CI does not deploy to AWS or establish physical-image accuracy.

This is a functioning local research prototype, not a finished hackathon entry. OpenCV `5.0.0` is verified in Python `3.12.10`. AWS deployment and the event's compute-proposal/registration gate remain unproven. No AI provider is connected.

## Run on Windows

From this directory in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m clearpath fixtures
.\.venv\Scripts\python.exe -m clearpath serve
```

Open **http://127.0.0.1:4181**. Activation is unnecessary. The local server binds only to `127.0.0.1` and rejects foreign origins. Uploaded images are processed in memory; the service does not save them.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m clearpath runtime
.\.venv\Scripts\python.exe -m clearpath evaluate
.\.venv\Scripts\python.exe -m clearpath inspect --fixture pinch
```

Use `python` instead of `.\.venv\Scripts\python.exe` inside an activated Linux virtual environment. All runtime dependencies are pinned; OpenCV's official headless `5.0.0.93` wheel supports Python 3.12 on Windows amd64 and Linux. [Official package](https://pypi.org/project/opencv-python-headless/5.0.0.93/). Do not install multiple packages sharing the `cv2` namespace.

## Try the demo

1. Inspect **Opposing obstacles**. The known planar gap is `0.75 m`; inspect both overlays and compare it with your chosen review target.
2. Try **Out-of-focus capture**, **Glare across the floor**, and **Camera moved after reference**. Each asks for another capture and withholds measurements.
3. Inspect **Known limitation: low-contrast object**. The detector misses it and overestimates the span by `1.00 m`. This is why a human checks every overlay.
4. Acknowledge your review and download the JSON report and annotated evidence.
5. For your own images, upload an aligned empty reference and scene, click four floor corners clockwise, enter measured dimensions, and inspect. The corners must represent a planar rectangle.

CLI image-pair inspection:

```powershell
.\.venv\Scripts\python.exe -m clearpath inspect --scene scene.png --reference empty.png --calibration calibration.json --output reports/my-inspection.json
```

`calibration.json` has `points` (four `[x,y]` coordinates in far-left, far-right, near-right, near-left order), `width_m`, `length_m`, and optional `review_width_m`. [Example calibration](docs/example-calibration.json) matches the owned 900 × 700 fixture images; replace the coordinates/dimensions for another photograph.

## Evidence and boundaries

29 vision/API tests passed, JavaScript syntax passed, and `pip check` passed. Browser visual QA is coordinated separately. [Evaluation](reports/evaluation.json) includes all nine owned synthetic fixtures and the low-contrast failure. Four normal planar fixtures yield mask IoU `1.0` and clearance mean absolute error `0.00 m`; these controlled round-trip fixtures **do not establish real-world accuracy**.

The measured span is the minimum, over floor rows, of each row's widest free segment. It does not guarantee a continuous route for a person, wheelchair, or vehicle. Changed-region projections are approximate footprints only for flat/contact regions; raised objects, shadows, reflections, unknown camera changes and similar colours can mislead the detector. The nominal raster is 1 cm, not a claim of 1 cm accuracy. This application does not certify accessibility, legal compliance or safety.

See [architecture](docs/ARCHITECTURE.md), [technical report draft](docs/REPORT.md), [demo script and submission gates](docs/HACKATHON.md), and [AWS deployment preparation](docs/AWS.md). The Linux container has passed a real local build, bearer-authentication checks, and a fixture inspection; [commands and runtime evidence](docs/CONTAINER_VERIFICATION.md). The AWS manifest targets ECS Express Mode and remains unvalidated and undeployed. Source and owned fixtures use [MIT](LICENSE); dependencies retain their own licenses.
