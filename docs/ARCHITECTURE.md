# ClearPath architecture

```mermaid
flowchart LR
  I[Scene + aligned empty view] --> G[Validate measured floor geometry]
  C[Four corners + width + length] --> G
  G --> Q[Focus / clipping / alignment checks]
  Q -->|insufficient| R[Request a new aligned capture]
  R --> I
  Q -->|accepted| H[OpenCV floor homography]
  H --> D[Reference difference + morphology]
  D --> O[Connected regions + floor occupancy]
  O --> M[Cross-section / area / point connectivity]
  M --> E[Annotated evidence + JSON]
  E --> U[Human reviews calibration and overlay]
  subgraph Local[Verified local CPU implementation]
    G
    Q
    H
    D
    O
    M
  end
  subgraph AWS[Prepared only: ECS Express Mode on Fargate]
    K[Same Python / OpenCV 5 container]
    S[HTTPS gateway + bearer token]
    S --> K
  end
  subgraph Lambda[Prepared only: private synchronous Lambda]
    P[IAM-authorized immutable image/version] --> A[Bounded event adapter]
    A --> K2[Same CPU OpenCV inspection]
    K2 --> J[Compact JSON + qualified receipt]
  end
```

`clearpath/vision.py` contains the actual image operations and measurements; the same function serves the CLI and Flask API. `fixtures.py` independently generates scene images, truth masks and labels. `evaluate.py` compares output masks and measurements against those labels. The fixture identifier only selects image inputs and calibration; the detector never reads ground-truth masks or expected answers.

The browser uses `GET /api/fixtures`, `GET /health`, and `POST /api/inspect`. JSON requests select a controlled fixture. Multipart requests carry two PNG/JPEG images and a calibration JSON object. Images are limited to 8 MB and 8 megapixels each. Reports include runtime evidence, capture requests, policy trace, quality values, measurements when accepted, PNG evidence, and limitations. The quality evidence includes separate scene/reference clipped fractions; either exceeding 22% requests recapture. Invalid calibration values, including numeric conversion overflow, return HTTP 400 with a JSON error. No upload persistence is implemented. A downloaded JSON adds the browser's human-review acknowledgment.

The recapture policy is deterministic: observed geometry or quality changes the next action from measurement to a specific capture request. It is not an LLM agent. Optional Agentic Vision eligibility must be confirmed before describing this policy as qualifying for that award.

`lambda_runtime.py` is a private synchronous adapter around the unchanged `vision.inspect` pipeline. It accepts owned fixtures or an aligned image pair, rejects URL inputs, caps each image at 2 MB and the event at 5.6 MB, and retains the shared eight-megapixel guard. Compact responses omit encoded images and preserve recapture decisions and limitations. Its receipt hashes the canonical request and LF-normalized vision source; context fields do not establish AWS execution. `lambda_evidence.py` separately prepares a plan without cloud calls or, after owner review, correlates one remote immutable-version Invoke with its configuration and platform log tail. [Exact local emulator verification and remaining cloud gates](LAMBDA.md). Neither prepared AWS route is currently deployed.
