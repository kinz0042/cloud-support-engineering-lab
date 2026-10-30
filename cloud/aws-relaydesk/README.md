# RelayDesk on temporary EC2

This optional exercise runs the existing API, PostgreSQL, worker and mock partner together on a disposable EC2 host. It is a single-host support lab, not a production hosting design. The bootstrap downloads a pinned repository revision, so later repository changes are not automatically included.

## Deployment contract

Use an authorized account, allowed region, existing internet-routed subnet, and a dedicated security group with **no inbound rules** and outbound HTTPS for package/image downloads. An automatically assigned public IPv4 address supplies outbound connectivity; this does not mean the application is publicly served. The Compose API remains bound to host loopback. Do not open port 8081 or SSH to the internet.

The executed configuration uses Amazon Linux 2023 x86_64, t3.small with standard CPU credits, IMDSv2 required, and one encrypted 20 GiB gp3 root volume with DeleteOnTermination. No instance profile, SSH key or static AWS credentials are required. Set InstanceInitiatedShutdownBehavior to terminate. The bootstrap schedules a 30-minute shutdown as a fallback; this is not a billing guarantee, and cleanup must still be independently verified.

Review [bootstrap.sh](bootstrap.sh) before supplying it as EC2 user data. Do not run it on a personal workstation or a shared server: it installs Docker and schedules host shutdown. With AWS CLI, the user-data file input is `--user-data file://bootstrap.sh`; with the EC2 API, encode the file as Base64. Inspect the exact launch parameters before calling RunInstances. Instance eligibility and resource availability depend on the account and region.

Docker comes from the Amazon Linux package repository. Compose is pinned to v5.6.1 and checked against the checksum file downloaded from the same official GitHub release. This catches mismatches but is not an independent signature-verification chain. The app source is pinned by commit; the container base image, PostgreSQL image tag, and Python dependency ranges remain mutable, so this is not a fully reproducible supply-chain build.

## Validation and cleanup

The bootstrap runs the repository's existing Compose smoke test. That test checks authenticated API access, tenant isolation, idempotent order submission, actual asynchronous mock delivery, signed callback deduplication/collision and database outage/recovery. It does not run the optional Keycloak or Prometheus profiles, external customer traffic, TLS, a managed database or high availability.

Success is indicated by `CSELAB_APP_SMOKE_PASSED` and then `CSELAB_APP_PASS` in the instance console. Failure is reported with `CSELAB_APP_FAILED`; a running instance alone does not prove deployment success. Inspect console output and its timestamp because output may lag. The exit trap attempts Compose cleanup; independent EC2 termination and disk/security-group checks are still mandatory.

The CloudWatch exercise uses an operator-side sanitized **batch export** of selected console/application events, followed by reading those events back. It is not a continuously running CloudWatch agent, alarm or alert notification integration. Do not upload raw console logs, host keys, infrastructure identifiers, credentials or customer payloads to a public repository.

After collecting evidence, terminate the instance, wait for its terminated state, check its root volume was removed, delete only the dedicated lab security group and log group, and check for leftover addresses. Preserve pre-existing VPC/subnet/default-group resources. Billing and credit consumption can lag.
