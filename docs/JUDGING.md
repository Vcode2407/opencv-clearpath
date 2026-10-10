# Reproduce ClearPath's local evidence

ClearPath is a working CPU OpenCV 5 prototype. The [2:30 English development video](media/clearpath-local-demo-en.mp4) shows real browser/API inspections of owned synthetic scenes, including a known measurement failure. It does not show AWS execution, field validation, or a completed qualifying entry. The [recording notes and transcript](DEMO.md) describe exactly what was captured.

## Start from the public repository

Use Python 3.12 and the pinned requirements. No account, provider key, cloud service or paid call is required for the local path.

Windows PowerShell:

```powershell
git clone https://github.com/Vcode2407/opencv-clearpath.git
cd opencv-clearpath
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m clearpath runtime
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m clearpath serve
```

Linux/macOS with Python 3.12 available:

```sh
git clone https://github.com/Vcode2407/opencv-clearpath.git
cd opencv-clearpath
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m clearpath runtime
.venv/bin/python -m pytest -q
.venv/bin/python -m clearpath serve
```

The recorded and automated verification environments are Windows and Ubuntu Linux; macOS has not been verified here. Open **http://127.0.0.1:4181**. If that port is occupied, start `serve --port 4196` and open the matching URL. The runtime output must report the actual `opencv_version`, rather than assuming the dependency installation succeeded. This recording reports `5.0.0`, CPU, `ai_provider: none`, and `aws_deployment_verified: false`.

The repository includes its generated fixture images and manifest. `python -m clearpath fixtures` regenerates the nine deterministic owned fixtures when needed. Their labels are separate evaluation inputs; the detector reads the scene, empty reference and calibration, not the expected answers.

## Three inspections to assess

Leave the review target at **1.2 m**. It is an operator comparison value, not a legal requirement.

| Browser action | Actual expected local response | What to assess |
| --- | --- | --- |
| Choose **Opposing obstacles**, then **Inspect this view**. | `review_required`; **0.75 m** cross-section, **1.65 m²** projected changed area, two changed regions. | Compare the source overlay with the calibrated floor view. The independent synthetic label matches these values. |
| Read the review limits, acknowledge review, then download the JSON report. | The browser export includes `human_review_acknowledged: true` and the same actual inspection. | Acknowledgement records the operator's action; it is not a certification. The checkbox is not an enforced export gate. |
| Choose **Out-of-focus capture**, then inspect. | `needs_capture`; a focus/alignment recapture request; **`measurements: null`**. The browser hides the previous metrics. | Check that the tool changes the next action and does not reuse the earlier measurement. |
| Choose **Known limitation: low-contrast object**, then inspect. | The detector misses the object and reports **2.40 m**, **0.00 m²**, zero changed regions. The independent label is **1.40 m** and **1.00 m²**. | This is a **1.00 m overestimate**, not a success. Inspect the missed object and retained evaluation failure. |
| Expand **How this inspection reached its result**. | Actual geometry, quality, projection, measurement and review trace plus limits. | The policy is deterministic; no language model is connected. |

The reported span is the minimum of each floor row's widest free interval. Adjacent rows can choose different intervals. It does not prove a continuous body-width route. Point connectivity is a separate, point-sized check. A one-centimetre raster is a sampling setting, not a measurement-accuracy claim.

## Reproduce without a browser

Inside the environment, replace `python` with the virtual-environment executable if it is not activated:

```sh
python -m clearpath inspect --fixture pinch --output reports/judge-pinch.json
python -m clearpath inspect --fixture blur --output reports/judge-blur.json
python -m clearpath inspect --fixture low_contrast --output reports/judge-low-contrast.json
python -m clearpath evaluate --output reports/judge-evaluation.json
```

These CLI inspections execute the same pipeline as the Flask API. The evaluation includes all nine scenes, not just the four ideal ones. See [stored evaluation](../reports/evaluation.json) and [technical report](REPORT.md). Nine expected statuses do not mean nine accurate measurements: low contrast has IoU **0.0** and a **1.00 m** span error.

The [GitHub workflow](../.github/workflows/verify.yml) runs the 29 vision/API tests, JavaScript syntax and dependency checks, actual runtime verification, and evaluation on Windows and Ubuntu. A separate job builds the Linux image, checks UID 10001, dependencies and OpenCV runtime. These checks are local/CI evidence; they do not establish an AWS location.

## Container evidence and remaining gates

The existing Dockerfile was genuinely built and run locally. Bearer-auth checks rejected missing/wrong tokens, then an authenticated pinch inspection performed server-side OpenCV 5 processing. See the exact commands and response details in [CONTAINER_VERIFICATION.md](CONTAINER_VERIFICATION.md). The `aws` configuration name selects the bearer-protected mode; it is not evidence of an AWS deployment.

The final entry still needs meaningful actual AWS execution, a judge endpoint or arranged screen-share, the final team/architecture/cloud video material, and human eligibility/participation confirmation. The organizer website describes a proposal gate and an August 17 registration close that the visible Devpost package does not resolve. Do not assume a Devpost registration satisfies it. [Official organizer requirements](https://opencv.org/opencv-ai-competition-2026/), [Devpost rules](https://opencv26.devpost.com/rules), and [submission gates](HACKATHON.md).

Physical-capture validation is also pending. No safety, accessibility compliance, field accuracy, special-award eligibility or submitted-entry claim is made.
