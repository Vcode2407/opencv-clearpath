# AWS deployment preparation — not executed

The intended meaningful AWS component is the **actual OpenCV CPU inspection** on ECS Express Mode/Fargate. Hosting only static screenshots would not establish that component. No AWS calls or deployment were performed during this build, and no credentials are stored in the project.

`Dockerfile` uses Linux Python 3.12 and a pinned OpenCV 5 headless wheel. `infra/ecs-express.yaml` provisions the Express service, task execution/infrastructure roles and a generated Secrets Manager bearer token. It sets port 4181, 1 vCPU/2 GB and one task. The API requires that token in cloud mode; the local CLI remains loopback-only. The template assumes a supported region with a default VPC/public subnets, an accessible ECR image and permissions for ECS, IAM, Secrets Manager and provisioned networking. Confirm these in the account before applying it.

AWS recommends ECS Express Mode as App Runner's replacement. App Runner is closed to new customers according to current official notices, so it is not the primary route for an account with unknown service history. Sources: [availability notice](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html), [Express Mode getting started](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html), [CloudFormation resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ecs-expressgatewayservice.html), [container schema](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-ecs-expressgatewayservice-expressgatewaycontainer.html).

## Validate locally first

The Linux image has been built and exercised on the local Docker Desktop engine, including missing/wrong-token rejection and an actual OpenCV 5 fixture inspection. [Recorded build identity, commands and results](CONTAINER_VERIFICATION.md). This validates local packaging; AWS execution remains pending. To repeat it:

```powershell
docker build -t clearpath:0.1 .
# Choose a fresh random token; keep it out of source control and recordings.
$env:CLEARPATH_API_TOKEN = '<fresh-random-token-at-least-24-characters>'
docker run --rm -p 127.0.0.1:4191:4181 -e CLEARPATH_API_TOKEN clearpath:0.1
```

Visit http://127.0.0.1:4191, enter the token, load fixtures, and inspect. Stop the retained verification container before reusing that port. This tests cloud-mode packaging locally; it does not prove AWS execution. The recorded verification includes the resolved base-image digest and build-input hashes; deployment preparation should additionally retain dependency artifact hashes and the final ECR image digest.

## Offline CloudFormation schema preflight

Checked **October 11, 2026** with Python **3.12.10** and [AWS CloudFormation `cfn-lint`](https://github.com/aws-cloudformation/cfn-lint) **1.57.2**, installed into an isolated environment from [official PyPI](https://pypi.org/project/cfn-lint/). The packaged schemas contain `AWS::ECS::ExpressGatewayService` for **us-east-1** and **ap-south-1**. Strict property-type checking with errors, warnings and informational checks enabled found **zero errors, zero warnings and two informational I3011 findings**. The unchanged template's SHA-256 is `a251f03f6c7c4194616766ecf7a3f220b7f6ec341d62bccd48ea919b375e5b87`.

Both informational findings concern the generated demo secret: no explicit `DeletionPolicy` or `UpdateReplacePolicy` is set. The existing default delete behavior is retained; this static review did not identify a schema defect requiring an infrastructure change. The validator exits 0 at the warning/error threshold and 8 when informational findings also fail the run. The actual review blocked socket connections and DNS resolution, observed zero network attempts, and made no AWS account calls. [CloudFormation lifecycle policies](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-attribute-deletionpolicy.html).

To reproduce the static checks from this project directory in a separate temporary environment:

```powershell
$taskLintVenv = Join-Path $env:TEMP 'clearpath-cfn-lint-1.57.2'
py -3.12 -m venv $taskLintVenv
& (Join-Path $taskLintVenv 'Scripts/python.exe') -m pip --isolated --disable-pip-version-check install --index-url https://pypi.org/simple cfn-lint==1.57.2
& (Join-Path $taskLintVenv 'Scripts/cfn-lint.exe') --template infra/ecs-express.yaml --regions us-east-1 ap-south-1 --include-checks I --mandatory-checks E W I --configure-rule E3012:strict=true --non-zero-exit-code warning
```

This checks the published package's resource schemas and local template expressions. It does **not** verify account permissions, actual regional service availability, ECR image access, quotas, network reachability, CloudFormation service-side validation or deployment. The official [resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ecs-expressgatewayservice.html), [container](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-ecs-expressgatewayservice-expressgatewaycontainer.html), [scaling](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-ecs-expressgatewayservice-expressgatewayscalingtarget.html) and [getting-started](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html) documentation agree with the configured roles, port, image/secret fields, CPU/memory, scaling metric and default-VPC assumptions. Actual AWS execution remains pending.

## Cloud milestone

With an authorized AWS account, build and push the tested image to that account's private ECR repository using its configured region and an immutable tag/digest. Review `infra/ecs-express.yaml`, the resources it provisions and account access. Deploy through CloudFormation with the ECR image URI and IAM capability. Retrieve the generated token from the stack's secret ARN privately; supply it to reviewers outside the public repository/video. Use the ECS console/service description to find the HTTPS application endpoint. The manifest has passed the offline schema preflight above; AWS service-side CloudFormation validation and deployment have not been performed.

After deployment, record the service/resource identifiers, image digest, actual endpoint health/runtime response and a successful **server-side inspection** with annotated output. Include an AWS console or CloudWatch trace tying that request to the real service, plus judge access and reproduction steps. Set `aws_deployment_verified` only after such evidence exists; current reports deliberately retain `false`.

Cloud compute, networking/load balancing, image storage and secret resources can incur charges while provisioned. Maintain the endpoint for judging, then remove this project's resources when no longer needed. No free-credit eligibility or account access is assumed.
