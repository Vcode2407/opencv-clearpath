# OpenCV AI Competition 2026 — ClearPath preparation

Official sources: [overview](https://opencv26.devpost.com/), [rules](https://opencv26.devpost.com/rules), [resources](https://opencv26.devpost.com/resources), [organizer website](https://opencv.org/opencv-ai-competition-2026/). Checked October 10, 2026.

The Devpost header lists **October 26, 2026, 11:45 pm PDT / October 27, 12:15 pm IST**. Body text and the organizer website instead say 11:59 pm Pacific / 12:29 pm IST. Plan for the earlier time until the organizer clarifies.

## Qualification gates

- [x] Actual OpenCV 5 substantive runtime: image validation, transformation, change detection, regions, connectivity and annotated evidence. Local runtime `5.0.0` verified.
- [ ] Meaningful AWS workload deployed and demonstrated. Container/template preparation alone does not meet this requirement.
- [ ] Confirm participation eligibility and compute-proposal status. The organizer website says registration closed August 17 and requires a compute-grant proposal; Devpost's visible submission requirements omit that proposal gate. Existing Devpost registration is not proof the website requirement was met.
- [ ] Confirm any relevant age/geography and cross-entry restrictions. Rules allow 13+ with guardian arrangements; the overview says age of majority and unspecified standard country exceptions.

Build this as a distinct project. No assertion is made that an identical entry can be reused across events. Work and owned fixtures are licensed; dependency licenses remain separate. Solo development avoids conflicting published team-size limits.

## Submission assets

- [x] Working local CPU application, browser, API and CLI.
- [x] Pinned dependencies, run/test instructions, owned fixture labels and automated evaluation.
- [x] Draft technical report and architecture diagram, with failures and responsible-use limitations.
- [x] Judge-accessible MIT repository: https://github.com/Vcode2407/opencv-clearpath. Public source is not mandatory for this event.
- [ ] Actual AWS deployment/reproduction instructions and runtime evidence.
- [ ] Working endpoint or arranged judge screen-share, with needed access details.
- [x] Actual **2:30 English local development video**, captions, transcript and response evidence: [recording](DEMO.md). Shows the application, principal synthetic results, recapture and known failure. It does not show an AWS deployment.
- [ ] Final judge-accessible video no longer than five minutes: add team introduction, architecture and genuine AWS runtime evidence, then verify public/unlisted playback access.
- [ ] Final report updated with physical-capture evaluation, deployment evidence, limitations and licensing.

Optional Agentic Vision award requires perception to alter subsequent actions; current deterministic quality gates produce recapture requests, but award eligibility has not been confirmed. Do not claim an LLM agent. COOL requires actual Graviton/Arm workload and measured baseline; it is outside the first milestone.

## Four-minute demo script

The completed [2:30 local development clip](DEMO.md) covers the core browser flow with actual response assertions. The outline below describes final additional material; AWS footage must come from actual execution.

0:00–0:30 — Introduce the temporary-obstruction evidence problem and controlled planar scope. Show actual OpenCV 5 runtime.

0:30–1:20 — Inspect opposing obstacles. Explain measured calibration, projected regions, 0.75 m cross-section and the chosen review target. Show the source overlay and floor view.

1:20–2:00 — Inspect blur, glare or moved-camera case. Show the quality evidence and action changing to a recapture request. Explain that measurements are withheld.

2:00–2:40 — Inspect low contrast. Show the actual missed region and 1.00 m overestimate against the label. Explain human review and limits.

2:40–3:20 — Upload an owned registered image pair, select corners and download evidence. Until physical capture data exists, label any fixture upload as synthetic.

3:20–4:00 — Show architecture, evaluation and actual AWS runtime/service evidence once deployed. If deployment is still pending, say so plainly; this is not yet a qualifying final submission.
