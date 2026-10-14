# Private Lambda preparation and local verification

ClearPath has a private synchronous Lambda adapter for the same CPU OpenCV inspection used by its browser and CLI. The pinned official AWS Python 3.12 container was built and exercised through its **local Runtime Interface Emulator on October 14, 2026**. This is packaging evidence; no function was deployed, no AWS account call was made, and no AWS runtime is claimed. The existing ECS Express Mode browser-hosting route remains available in [AWS.md](AWS.md).

The Lambda route avoids provisioning a web gateway for an initial reviewed inspection. `infra/lambda.yaml` prepares a 2,048 MB, x86_64 image function with a 60-second timeout, 512 MB temporary storage, a seven-day log group, a logging-only execution role and an immutable published version. The function has no Function URL, load balancer, VPC attachment or provisioned concurrency. Same-account IAM authorization is still required to invoke it. Reserved concurrency is omitted by default; the optional value `1` requires an account-quota review. Image/account/service availability and permissions remain unverified. The template supports conventional commercial AWS regions, not China or government partitions.

## Input and output

`clearpath.lambda_runtime.handler` accepts either an owned fixture event:

```json
{"fixture":"pinch","review_width_m":1.2}
```

or an aligned PNG/JPEG pair with plain base64 fields `scene_base64`, `reference_base64` and a `calibration` object. The calibration uses the existing four corner points, measured `width_m`/`length_m`, and optional `review_width_m`. URLs, file paths, data URLs and unknown event fields are refused. Each compressed image is limited to 2,000,000 bytes and the canonical JSON event to 5,600,000 bytes; both decoded images retain the shared eight-megapixel preallocation guard. These deliberately fit below the [synchronous Lambda payload quota](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html).

One accepted invocation performs one actual CPU inspection with one OpenCV worker thread. The response omits the three encoded image fields and is limited to 500,000 JSON bytes. It preserves quality decisions, measurements, limitations, capture requests and actual runtime data. Blur, glare and moved-camera fixtures still withhold measurements. The low-contrast fixture still misses an object and overestimates the span by **1.00 m**. Inspect the local image overlays alongside the compact report; a JSON receipt does not replace that human review or establish physical-image accuracy.

The execution receipt hashes the canonical event and the vision source. Vision source hashing normalizes CRLF to LF to permit consistent Windows/Linux comparison; the receipt states this normalization explicitly. Runtime context identifiers are observations only: `aws_execution_verified` and the shared `aws_deployment_verified` remain **false**, including under the emulator or an injected context.

## Repeat the local package check

From the project directory with Docker's Linux engine running:

```powershell
docker build --platform linux/amd64 --provenance=false -f Dockerfile.lambda -t clearpath-lambda:local .
docker run --rm -d --name clearpath-lambda-local --platform linux/amd64 --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m --cap-drop ALL --security-opt no-new-privileges --user 10001:10001 --memory 2048m --cpus 1 -e PYTHONDONTWRITEBYTECODE=1 -p 127.0.0.1:4197:8080 clearpath-lambda:local
Invoke-RestMethod -Uri 'http://127.0.0.1:4197/2015-03-31/functions/function/invocations' -Method Post -ContentType 'application/json' -Body '{"fixture":"pinch"}'
Invoke-RestMethod -Uri 'http://127.0.0.1:4197/2015-03-31/functions/function/invocations' -Method Post -ContentType 'application/json' -Body '{"fixture":"blur"}'
Invoke-RestMethod -Uri 'http://127.0.0.1:4197/2015-03-31/functions/function/invocations' -Method Post -ContentType 'application/json' -Body '{"fixture":"low_contrast"}'
docker stop clearpath-lambda-local
```

The official base includes its runtime client and emulator. AWS's [Python image guide](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html) requires a single target architecture and `--provenance=false` for Lambda compatibility. An initial local build with default provenance emitted an attestation index; its log was retained and the tested image was rebuilt with the explicit flag. The emulator is [a local development tool](https://github.com/aws/aws-lambda-runtime-interface-emulator); its platform-looking request IDs, log lines and memory/billing figures are not proof of AWS execution or actual cloud charges. Its error payload, rather than HTTP 200 alone, identifies a refused invocation.

The recorded final image ran as UID/GID `10001:10001`, with a read-only root filesystem, an in-memory `/tmp`, no host bind mounts, a loopback-only port, and local Docker limits of 2 GB/one CPU. Six owned fixture calls verified pinch/edge-box measurements, three quality refusals and the retained low-contrast failure. Four additional emulator calls refused a remote URL, a data URL, a pixel-bomb header and an oversized event. `pip check` found no broken requirements. [Exact local runtime/build identity and results](lambda-local-verification.json).

The complete local suite now has **66 passing tests**: the original 31 vision/API tests plus 35 Lambda schema, image-boundary, receipt and one-attempt tests. The receipt tests use an injected subprocess transport in temporary test directories; they are not AWS evidence. JavaScript syntax and dependency checks also passed. Existing recording/evaluation assets retain their historical test counts and source evidence.

## Offline template review

The prepared manifest, including its published-version resource, passed strict packaged CloudFormation schema checks for `us-east-1` and `ap-south-1` using existing isolated `cfn-lint` 1.57.2. All error, warning and informational rules were enabled. The validation blocked socket connections and DNS resolution, observed zero network attempts, and returned zero findings. [Dated template identity and result](lambda-offline-schema.json). This does not establish AWS permissions, quotas, image access, service-side acceptance or deployment.

## Review an actual cloud milestone

AWS account setup, authorization for resource creation/spending, private ECR upload, service-side validation and deployment are still owner steps. Before proceeding, review the exact account/region, tested source, final single-architecture ECR image digest, stack resource plan and potential Lambda/ECR/log charges. The template publishes a version, returns its number and qualified ARN, and changes the version description when the image digest changes. Review the image/version mapping after deployment; [CloudFormation versions](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-lambda-version.html) snapshot code and configuration. A private function alone supplies no public judge endpoint; arrange a judge screen-share or another reviewed access route separately.

`clearpath.lambda_evidence` defaults to **preparation only**. It validates the owned event locally and writes a new evidence directory without starting AWS CLI or reading account credentials. For example, replace every illustrative account/image value below with the specifically reviewed deployed target before use:

```powershell
'{"fixture":"pinch"}' | Set-Content -Encoding utf8 artifacts/lambda-event.json
.\.venv\Scripts\python.exe -m clearpath.lambda_evidence --function-arn arn:aws:lambda:ap-south-1:123456789012:function:clearpath-inspect --version 1 --image-uri 123456789012.dkr.ecr.ap-south-1.amazonaws.com/clearpath@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --region ap-south-1 --profile owner-reviewed-profile --event artifacts/lambda-event.json --output artifacts/lambda-prepared-plan
```

After approval, keep the reviewed target/event unchanged, choose a **fresh different** `--output` directory and append `--execute-one-call`. This requests one configuration read and, only if the active version/digest/architecture/memory/timeout match, one chargeable synchronous Invoke. It is a distinct owner-reviewed step, not part of local setup. The command disables CLI retries (`AWS_MAX_ATTEMPTS=1`), selects the explicit official HTTPS Lambda endpoint with TLS verification, uses finite client/process timeouts, and never retries an unknown outcome. Credential-provider authentication or renewal can occur through the owner's existing CLI profile; no credentials are copied into source or evidence.

The collector requires successful Invoke metadata, the exact executed version, matching event/source hashes and qualified context, actual CPU OpenCV 5 runtime, and matching START/END/REPORT request IDs and version from the returned platform log tail. [Invoke response semantics](https://docs.aws.amazon.com/cli/latest/reference/lambda/invoke.html) require checking function errors as well as status. The configuration read obtains the resolved image from [GetFunction](https://docs.aws.amazon.com/cli/latest/reference/lambda/get-function.html). Only that separately captured, reviewed remote result can mark the collector receipt as verified; the handler's generic runtime flags remain false. This is correlated service evidence, not a cryptographic attestation or a field-accuracy result.

Evidence collection intentionally saves the selected request and response locally, together with bounded configuration/metadata and filtered platform lines. Use owned synthetic fixtures for the initial milestone, keep the output directory private/ignored, and review it before any publication. Existing output directories are refused to preserve prior attempts. If the Invoke outcome is uncertain or any integrity check fails, retain the attempt as unverified and investigate the known request; do not repeat it automatically. Current repository records show **no AWS account call, upload, deployment, charged invocation or final judge access**.
