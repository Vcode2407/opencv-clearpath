# AWS deployment preparation — not executed

The intended meaningful AWS component is the **actual OpenCV CPU inspection** on ECS Express Mode/Fargate. Hosting only static screenshots would not establish that component. No AWS calls or deployment were performed during this build, and no credentials are stored in the project.

`Dockerfile` uses Linux Python 3.12 and a pinned OpenCV 5 headless wheel. `infra/ecs-express.yaml` provisions the Express service, task execution/infrastructure roles and a generated Secrets Manager bearer token. It sets port 4181, 1 vCPU/2 GB and one task. The API requires that token in cloud mode; the local CLI remains loopback-only. The template assumes a supported region with a default VPC/public subnets, an accessible ECR image and permissions for ECS, IAM, Secrets Manager and provisioned networking. Confirm these in the account before applying it.

AWS recommends ECS Express Mode as App Runner's replacement. App Runner is closed to new customers according to current official notices, so it is not the primary route for an account with unknown service history. Sources: [availability notice](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html), [Express Mode getting started](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html), [CloudFormation resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ecs-expressgatewayservice.html), [container schema](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-ecs-expressgatewayservice-expressgatewaycontainer.html).

## Validate locally first

Docker CLI is installed here, but the Linux daemon was unavailable. These commands are preparation, not completed validation:

```powershell
docker build -t clearpath:0.1 .
# Choose a fresh random token; keep it out of source control and recordings.
$env:CLEARPATH_API_TOKEN = '<fresh-random-token-at-least-24-characters>'
docker run --rm -p 127.0.0.1:4182:4181 -e CLEARPATH_API_TOKEN clearpath:0.1
```

Visit http://127.0.0.1:4182, enter the token, load fixtures, and inspect. This tests cloud-mode packaging locally; it does not prove AWS execution. The base-image tag is pinned to a Python patch release, but release preparation should also record its digest and dependency artifact hashes.

## Cloud milestone

With an authorized AWS account, build and push the tested image to that account's private ECR repository using its configured region and an immutable tag/digest. Review `infra/ecs-express.yaml`, the resources it provisions and account access. Deploy through CloudFormation with the ECR image URI and IAM capability. Retrieve the generated token from the stack's secret ARN privately; supply it to reviewers outside the public repository/video. Use the ECS console/service description to find the HTTPS application endpoint. The manifest has not been CloudFormation-validated or deployed yet.

After deployment, record the service/resource identifiers, image digest, actual endpoint health/runtime response and a successful **server-side inspection** with annotated output. Include an AWS console or CloudWatch trace tying that request to the real service, plus judge access and reproduction steps. Set `aws_deployment_verified` only after such evidence exists; current reports deliberately retain `false`.

Cloud compute, networking/load balancing, image storage and secret resources can incur charges while provisioned. Maintain the endpoint for judging, then remove this project's resources when no longer needed. No free-credit eligibility or account access is assumed.
