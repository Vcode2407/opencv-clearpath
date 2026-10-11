# ClearPath — English Devpost submission draft

Prepared October 10, 2026. This is a working local research prototype and an unpublished draft for the OpenCV AI Competition 2026. Real CPU OpenCV 5 is verified. AWS execution and the organizer's participation/proposal gate remain unverified; this document does not claim a qualifying or submitted entry.

## Project name and tagline

**ClearPath**

**Measure changed walkway regions—and show when the image needs another capture.**

Intended entry: the overall competition. No COOL/Graviton or Agentic Vision award eligibility is claimed.

## Inspiration and problem

A photograph of a temporary walkway obstruction can show that something changed without establishing how much floor space it occupies or whether the capture is suitable for measurement. Perspective, camera movement, glare, and low contrast can make an apparently precise result misleading.

ClearPath explores an evidence-first inspection workflow for a controlled, measured floor rectangle. It compares an aligned empty reference with a scene, projects changed regions onto the floor plane, and shows the measurements beside the annotated images and capture warnings. It is a product hypothesis for people documenting temporary obstructions; no customer interviews, field deployments, or measured user outcomes are claimed.

## What actually works

The local browser, Flask API, and CLI run the same CPU vision pipeline. An operator supplies an aligned empty reference and scene, identifies four floor corners, and enters measured width and length. The rectangle must represent a planar floor region. Controlled fixtures are also available for a reproducible demo.

Geometry and image-quality gates can request another capture and withhold measurements. Accepted captures show changed regions, projected area, the narrowest row-wise widest free segment, and a separate point-connectivity result. The browser displays both the source overlay and rectified floor view. A human checks the calibration, overlays, assumptions, and limits before acknowledging review and downloading evidence.

Uploads are processed in memory and are not saved by the service. The local server binds to localhost. The operator explicitly chooses when to download a report or annotated evidence.

## Technical architecture

The verified runtime is Python 3.12.10 with `opencv-python-headless` 5.0.0.93; `cv2.__version__` reports **5.0.0**. NumPy supports the occupancy calculations, and Flask exposes the inspection API. The dependencies are pinned.

OpenCV validates the floor geometry and checks focus, clipping, background change, and phase-correlation alignment. It then rectifies accepted images using `getPerspectiveTransform` and `warpPerspective`, detects reference differences with `absdiff`, applies morphological opening/closing, and finds connected regions. Row-wise free intervals produce the reported projected span. A separate connected-component check asks whether a point-sized free region links the near and far floor boundaries.

The detector consumes images and calibration, not expected answers. The fixture generator separately creates owned synthetic scenes and truth masks; the evaluation compares the detector's results with those labels. Reports include runtime information, policy decisions, quality values, measurements when accepted, annotated images, and limitations.

An ECS Express Mode/Fargate container and infrastructure manifest are prepared for the same OpenCV CPU workload on AWS. The Linux image has now passed a real local build, bearer-authentication checks, and a server-side OpenCV fixture inspection; [recorded evidence](CONTAINER_VERIFICATION.md). The cloud manifest remains unvalidated and undeployed, and no AWS runtime is claimed. Actual cloud execution and judge access remain pending.

## Measured local results

The stored evaluation covers **nine deterministic owned synthetic fixtures**, generated from a known 2.4 × 6.0 metre plane. These are controlled, exactly registered round-trip scenes, not independent photographs or real-world validation.

| Evidence | Actual local result | Meaning |
| --- | --- | --- |
| Four normal planar fixtures | Mean mask IoU 1.0; projected-span mean absolute error 0.00 m at the fixture raster. | Implementation consistency under ideal synthetic conditions, not a general accuracy claim. |
| Opposing obstacles | Known and reported span 0.75 m. | A reproducible planar-gap example. |
| Blur, glare, moved camera, tiny calibration | Specific recapture requests; measurements withheld. | Tested quality/geometry decisions change the next action. |
| Low-contrast object | Missed object; IoU 0.0; true span 1.40 m, reported 2.40 m. | A substantive **1.00 m overestimate** that remains visible in the evaluation. |

The evaluation's nine expected workflow statuses do not mean nine accurate measurements. The low-contrast case is a failure even though its expected status is `review_required`. The README records 31 passing vision/API tests, a passing JavaScript syntax check, and a passing dependency check. The added regressions reject glare in the empty reference without false measurements and return an actionable error for overflowing calibration numbers. See [evaluation JSON](../reports/evaluation.json) and the [technical report](REPORT.md).

## Development challenges

The main challenge was defining a measurement the current method can support. A row's widest free segment can occur at a different horizontal position from the next row's segment. Its minimum width is therefore not proof of a continuous route for a person or wheelchair. ClearPath reports that cross-section measure separately from point connectivity and explains both limits.

Another challenge was testing failure decisions as part of the product. Focus, glare, alignment, and geometry fixtures require a new capture rather than returning a number. The tests check that those cases have no measurements. The low-contrast fixture is deliberately retained to expose what the difference detector misses; it is not removed to improve the headline benchmark.

Input boundaries also needed concrete tests. The suite rejects crossed calibration corners, invalid dimensions, mismatched reference sizes, unsupported image data, and excessive pixel counts before decoding large images. API tests cover upload handling, local-origin checks, restricted paths, and the prepared cloud-token boundary.

## What the implementation demonstrates

The prototype combines substantive OpenCV operations with a visible review workflow and reproducible local evidence. It demonstrates that a useful inspection tool must explain why it withheld a measurement and retain known failures alongside successful examples.

The recapture policy is deterministic. It changes the next action using observed image evidence; it is not an LLM agent. Whether this policy meets the event's optional Agentic Vision requirements remains an organizer question, not a claim in this draft.

## Limits and next steps

ClearPath detects image changes, not semantic obstacles. The projection assumes a planar floor and mapped flat/contact regions. Raised objects, shadows, reflections, similar colours, and unrecognized camera changes can mislead it. Four corner points do not independently estimate calibration uncertainty. The nominal one-centimetre raster is a sampling choice, not an accuracy guarantee.

The application does not certify accessibility, legal compliance, route safety, or body-width traversal. Human review cannot turn the current synthetic results into a certification. Before practical use, collect owned physical captures with measured markers, varied lighting and camera poses, repeated annotations, and held-out error analysis.

The Linux image is tested locally. The entry still needs actual AWS processing evidence, judge access, and confirmation of the proposal/registration requirements. No AWS credentials, credit eligibility, deployment, or Graviton performance comparison are assumed.

## Recorded development demo and final outline

The [2:30 silent, English-captioned local development video](media/clearpath-local-demo-en.mp4) shows actual CPU OpenCV 5 inspections, reviewed JSON export, recapture with no metrics, and the low-contrast 1.00 m overestimate. [Caption text and response evidence](DEMO.md), [judge reproduction guide](JUDGING.md). It uses owned synthetic fixtures and explicitly discloses AWS/eligibility as pending. The audio track has been removed; the actual screen footage and captions are unchanged.

This is a local development clip, not the final qualifying video. The final entry still needs team introduction, architecture and genuine AWS footage, plus verified judge-accessible playback. The proposed four-minute outline below includes those additions.

| Time | Action to record |
| --- | --- |
| 0:00–0:30 | Introduce the controlled walkway problem and show the actual CPU OpenCV 5 runtime. |
| 0:30–1:20 | Inspect opposing obstacles. Explain the measured rectangle and 0.75 m projected cross-section; show both overlays. |
| 1:20–2:00 | Run blur, glare, or moved-camera fixtures. Show a specific recapture request and absent measurements. |
| 2:00–2:40 | Run the low-contrast case. Show the missed region and 1.00 m overestimate against the label; explain the limitation. |
| 2:40–3:20 | Upload an owned aligned pair, choose corners, inspect, acknowledge review, and download evidence. Label synthetic uploads explicitly until physical captures exist. |
| 3:20–4:00 | Show the architecture and full evaluation. Add real AWS service/runtime evidence only after deployment; otherwise state that this gate is pending. |

## Fields and links still to complete

| Material | Draft value or pending work |
| --- | --- |
| Name and tagline | ClearPath; draft above. |
| English description | Draft above; review before pasting. |
| Technical report and architecture | Local drafts exist; update with physical-capture and actual AWS evidence. |
| Source repository/archive | https://github.com/Vcode2407/opencv-clearpath — public MIT source, owned fixtures and reproducible setup. |
| Working endpoint or arranged screen-share | Local `http://127.0.0.1:4181`; final judge-access arrangement pending. |
| Actual AWS workload/deployment evidence | Linux image and local server-side inspection verified; actual AWS deployment, resource identifiers, hosted inspection and judge access pending. |
| Video, no longer than five minutes | Actual 2:30 local English development MP4, captions, transcript and evidence exist in the public source. Final team/architecture/AWS footage and verified public/unlisted playback URL remain pending. |
| Measured results | Synthetic evaluation exists; physical-capture evaluation pending. |
| Compute proposal / registration gate | Organizer confirmation and evidence pending. Devpost registration alone does not establish this requirement. |
| Special awards | None claimed; COOL/Arm and Agentic Vision eligibility unverified. |
| Team, rights, consent, eligibility | Human verification pending. |
| Final Devpost URL/status | Pending; no submitted entry is claimed. |

Use the earlier displayed deadline for planning: **October 26, 2026, 11:45 pm PDT / October 27, 12:15 pm IST**. The organizer website says 11:59 pm Pacific, so the discrepancy needs confirmation. The website also describes an August 17 registration close and a required proposal, while Devpost's visible package differs; this participation gate remains unresolved. [Official rules](https://opencv26.devpost.com/rules), [organizer requirements](https://opencv.org/opencv-ai-competition-2026/), and [local submission gates](HACKATHON.md).
