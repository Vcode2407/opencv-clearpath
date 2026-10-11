# ClearPath local development recording

[Play/download the silent English-captioned MP4](media/clearpath-local-demo-en.mp4) · [Captions](media/clearpath-local-demo-en.srt) · [Actual response evidence](media/clearpath-recording-evidence.json) · [Judge reproduction guide](JUDGING.md)

This **2 minute 30 second** recording demonstrates the working local application, not a complete qualifying final submission. It uses the actual Python CPU OpenCV **5.0.0** pipeline and three owned synthetic fixtures. No AWS runtime, language model, paid service, external account or physical-capture result is depicted.

The browser is an isolated local Chromium session at `http://127.0.0.1:4196`. The recording drives the real controls and captures actual `/health` and `/api/inspect` responses; it does not substitute response stubs or draw invented application results. The same source is available at [Vcode2407/opencv-clearpath](https://github.com/Vcode2407/opencv-clearpath). A previously completed [Linux container verification](CONTAINER_VERIFICATION.md) is separate evidence, not part of the browser recording.

The current MP4 is silent: its audio track has been removed while preserving the actual screen footage and English captions. Captions occupy an added footer beneath the unchanged browser viewport. No result overlays conceal the low-contrast output. The low-contrast comparison comes from the independent owned fixture manifest, not an expected answer supplied to the detector.

## Recorded actions

The [silent-video verification](media/silent-video-verification.json) records zero audio streams, the current file hash, a complete decode, and an unchanged encoded video stream.

| Time | Real action and visible evidence |
| --- | --- |
| 0:00–0:14 | Open the application and wait for actual `OpenCV 5.0.0 · CPU · local` runtime. Disclose owned synthetic data and pending AWS/eligibility. |
| 0:14–0:32 | Inspect **Opposing obstacles**: 0.75 m span, 1.65 m² area, two changed regions. |
| 0:32–0:48 | View the source overlay and calibrated floor projection; explain the row-wise measure and route limit. |
| 0:48–1:04 | Check the review acknowledgement and download the actual JSON report. Assert acknowledgement and unchanged 0.75 m result. |
| 1:04–1:24 | Inspect **Out-of-focus capture**: real recapture request, `measurements: null`, previous metrics hidden in the browser. |
| 1:24–1:38 | View the focus/alignment request and explain the deterministic next action. |
| 1:38–1:56 | Inspect **Known limitation: low-contrast object**: reported 2.40 m with zero detected regions versus independent truth 1.40 m. |
| 1:56–2:14 | Show the missed region and explicitly disclose the 1.00 m overestimate; do not treat the green result as success. |
| 2:14–2:30 | Expand the actual vision trace and review limits. Disclose actual AWS processing, field validation and eligibility as pending. |

Inspection actions can take a fraction of a second after the scheduled boundary. The evidence JSON records actual action offsets. The reviewed export is verified by parsing the downloaded JSON, not just by observing a download animation. The public evidence preserves the actual reports, replacing PNG data URLs with explicit omission markers and removing the local raw-video path. The images remain visible in the video.

## Verification and limits

- The complete isolated-browser workflow passed assertions for runtime, response status, pinch measurements, reviewed export, recapture requests, absent retry metrics, and the low-contrast error.
- At recording time, 29 vision/API tests passed locally. [CI](https://github.com/Vcode2407/opencv-clearpath/actions) separately verifies Windows, Ubuntu and the non-root Linux container; those are not AWS deployments.
- The final MP4 is decoded in full with FFmpeg, and keyframes are visually checked for readable captions and genuine outputs. [Media manifest](media/manifest.json) records format, duration, SHA-256 and verification results.
- This clip does not supply final team introduction, AWS architecture/runtime footage, cloud judge access, physical-capture validation or eligibility confirmation. Those final materials remain pending under [submission gates](HACKATHON.md).

The tool detects changes, not semantic obstacles. Planar projection, lighting, alignment, shadows, reflections and low contrast limit it. Human review does not certify accessibility, safety or body-width traversal. The included failure is evidence of this limitation, not a claimed robustness result.

## English caption text

**0:00–0:14** — ClearPath compares a scene with an aligned empty reference. This is a local development recording of real CPU OpenCV five, using owned synthetic fixtures. AWS deployment and eligibility remain pending.

**0:14–0:32** — The opposing-obstacles fixture has a measured two point four by six metre floor. The real inspection reports a zero point seven five metre cross-section and one point six five square metres of changed area.

**0:32–0:48** — The overlays show the detected changes and calibrated floor projection. This number is the smallest of each row's widest free segments. It does not prove a continuous route for a person or wheelchair.

**0:48–1:04** — I acknowledge reviewing the calibration, overlay, and limits, then download the actual report. Review records an acknowledgement; it does not turn a synthetic result into a safety certification.

**1:04–1:24** — Now the out-of-focus capture. The quality gate requests another view instead of releasing a measurement. The API returns no metrics, and the browser hides the old numbers.

**1:24–1:38** — Recapture is an actual decision from image evidence. The operator must supply a better aligned image pair. This policy is deterministic, with no language model connected.

**1:38–1:56** — The low-contrast case exposes a failure. The detector misses the object and reports two point four metres, even though the independent fixture label is one point four metres.

**1:56–2:14** — That is a one metre overestimate. The green result is misleading here. We retain this case in evaluation and disclose it rather than claim general accuracy from ideal synthetic fixtures.

**2:14–2:30** — The trace records actual OpenCV operations and review limits. The Linux container is separately verified locally. Actual AWS processing, physical-capture validation, and organizer eligibility confirmation remain pending.
