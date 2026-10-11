# Technical report draft — ClearPath

Status: local CPU prototype validated on owned synthetic scenes; live AWS and organizer eligibility checks are pending. This draft must be updated with real capture/deployment evidence before submission.

## Problem and intended users

Operators documenting temporary walkway obstructions need measurable evidence and an explanation of when an image is unsuitable. ClearPath gives a human reviewer floor-projected changed regions and a cross-section comparison. The initial scope is controlled planar scenes with a static camera and measured floor rectangle, rather than arbitrary street photographs.

## Method

An operator supplies an empty reference, a scene captured from the same position, clockwise floor corners and physical dimensions. OpenCV validates a convex, adequately visible calibration rectangle. Laplacian focus variance, separate clipped-pixel fractions for the scene and empty reference, background difference and phase correlation flag unreliable captures. More than 22% clipped floor pixels in either image requests recapture; reference glare must not become a measured obstruction in an otherwise clear scene. A failure returns a specific recapture request and no measurement. Invalid calibration numbers, including conversion overflow, produce an actionable HTTP 400 JSON error in the API.

Accepted images are rectified with `getPerspectiveTransform` and `warpPerspective` at a nominal 100 pixels per metre. `absdiff` detects changed pixels above a 35-level channel threshold. Morphological opening/closing reduces noise; connected-component analysis removes regions smaller than 0.004 m² and reports projected areas/bounds. For each row, the algorithm finds free intervals. The smallest row-wise widest free interval is the reported span. Connected-component analysis separately tests whether a point-sized free component links the near and far boundaries. That connectivity is not a body-width traversal result.

Evidence is projected back onto the source image and shown on a rectified floor view. A reviewer checks the calibration, overlay, assumptions and limitations before acknowledging review. The comparison target is user-selected and not a legal threshold. [Architecture diagram](ARCHITECTURE.md).

## Actual evaluation

Environment: Python 3.12.10, NumPy 2.3.5, `opencv-python-headless` 5.0.0.93; `cv2.__version__` reports **5.0.0**. [Runtime evidence](../reports/runtime.json). Run `python -m clearpath evaluate` to regenerate [full evaluation](../reports/evaluation.json).

Nine deterministic, owned synthetic fixtures use a known 2.4 × 6.0 m plane projected into a perspective image. Label masks and dimensions come from the original geometry, separately from detection. Four normal scenes — empty, edge boxes, opposing obstacles, full-width obstruction — have mean mask IoU **1.0** and clearance MAE **0.00 m** at the fixture raster. These ideal, exactly registered round-trip scenes test implementation consistency; they are not independent photographs or evidence of general accuracy.

| Case | Actual behavior | Evidence |
|---|---|---|
| Empty plane | Review required; 2.40 m span | No detected change |
| Edge boxes | Review required; 1.80 m span | Two projected regions, 0.89 m² total |
| Opposing obstacles | Review required; 0.75 m span | Two regions, 1.65 m² total |
| Full-width obstruction | Review required; 0.00 m span | No connected point route |
| Blur | New capture requested; no measurement | Focus gate |
| Glare | New capture requested; no measurement | Clipping gate |
| Moved camera | New aligned pair requested; no measurement | Phase-correlation/background gate |
| Tiny calibration | Better angle requested; no measurement | Geometry gate |
| Low-contrast object | **Missed object; span overestimated by 1.00 m** | IoU 0.0; true span 1.40 m, reported 2.40 m |

All nine cases meet their explicitly defined status expectations; that statistic counts workflow decisions and **does not mean nine accurate measurements**. The missed low-contrast case remains a substantive failure. 31 automated tests cover fixture measurements, recapture decisions (including glare in the empty reference), input validation and calibration overflow, image limits, upload API, path restrictions, local-origin checks and cloud-token enforcement. Browser visual QA is tracked separately.

## Limitations and responsible use

The application detects image changes, not semantic obstacles. Projection assumes a planar floor and mapped contact/flat regions; raised objects can overproject. Similar colours can be missed; moving shadows, glare and floor texture can create false regions. Phase correlation catches tested global camera translation but is not a guarantee of unchanged pose. Four corner correspondences give no independent calibration-error estimate. One-centimetre sampling is not an accuracy guarantee, and cross-section width is not a continuous clearance route. Human review cannot convert these results into a certification.

Before real-world use, acquire owned registered physical captures with measured flat markers, lighting variations, perspective changes and repeated annotations. Report errors and failures on held-out captures, including calibration uncertainty. Do not use the current prototype for safety-critical routing or accessibility/legal decisions. Images are processed in memory; CLI operators explicitly choose which reports to save. Use synthetic or consented imagery in the demo.

## AWS deployment status

The same actual OpenCV 5 pipeline is containerized for meaningful AWS CPU processing on ECS Express Mode/Fargate; this is prepared infrastructure, **not a deployed service**. The Linux image built successfully on Docker Desktop and passed bearer-authentication probes and an actual opposing-obstacles inspection, returning 0.75 m and 1.65 m². [Build identity and local container evidence](CONTAINER_VERIFICATION.md). A generated Secrets Manager token is prepared for deployment. The cloud manifest has not been validated or deployed. No AWS calls, credentials or provider-model calls were used. [Deployment preparation and required evidence](AWS.md).

## Remaining entry work

Verify the organizer's proposal/registration requirements, deploy and record real AWS execution, add owned physical capture evaluation, finish judge access instructions, and record an English demo up to five minutes. No COOL/Graviton award, real-world accuracy or live AWS claim is currently made. [Submission checklist](HACKATHON.md).
