# RelayDesk EC2 run — 30 October 2026

This is an assistant-executed deployment of the synthetic lab in the owner's AWS account, not production experience or an independently completed learner investigation.

## Deployed scope

The core RelayDesk stack ran on Amazon Linux 2023 in Stockholm using repository commit `837c5a86a92b5fa23c055eb5a1554737ef138189`. API, PostgreSQL, webhook worker and mock partner ran together through Docker Compose. A local override reused one built application image. No application source change was required.

The temporary host used t3.small, standard CPU credits, IMDSv2, an encrypted 20 GiB root disk with deletion on termination, and a dedicated security group with no inbound rules and outbound HTTPS. It had an automatically assigned public IPv4 address for downloads; the API was bound to loopback and was not served publicly. No SSH key, IAM instance profile, static credentials, NAT gateway or load balancer was created.

The bootstrap scheduled termination after 30 minutes as a fallback. Actual cleanup was performed and checked separately. A fallback script is not a hard cost cap.

## Observed validation

The selected console output included:

```text
Compose API, tenant isolation, order replay, delivery, callback deduplication and database recovery passed
CSELAB_APP_SMOKE_PASSED
CSELAB_SOURCE_REVISION=837c5a86a92b5fa23c055eb5a1554737ef138189
Docker version 25.0.14, build 0bab007
Docker Compose version v5.6.1
CSELAB_APP_PASS
```

The final output was retrieved at 20:30:50 UTC. The Docker package transaction and CLI version reported different version strings; the CLI output above is preserved as observed, rather than inferred from the package name. Console output was delayed and sometimes duplicated by cloud-init.

The smoke script exercised API health/readiness, valid and invalid credentials, tenant separation, repeated external-ID submission, actual worker delivery to the mock partner, signed callback duplicates and a conflicting event ID, and stopping/restarting PostgreSQL with read recovery. It was the existing `scripts/compose_smoke.py`, not the entire unit suite or all optional profiles. Selected application logs included a delivered attempt with receiver status 202, order creation 201, callback conflict 409 and duplicate callback 202.

## CloudWatch verification

An operator-side script extracted JSON events from the instance console, selected only known application event types and fields, and deduplicated duplicated console lines. It uploaded ten selected application events plus one explicitly labelled deployment-summary event to a temporary CloudWatch Logs stream. GetLogEvents returned all **11 events**. Event timestamps used the export time, not reconstructed original occurrence times. This demonstrates batch log ingestion/readback; it is not an agent, live shipping, complete history, alarm, metric or notification-delivery test.

The temporary log group had one-day retention and was then explicitly deleted after readback. Raw boot logs, host keys, account identifiers and network addresses are not included in the public evidence.

## Failures handled during setup

- The first requested t3.medium size was rejected by the Free plan. DescribeInstanceTypes identified eligible sizes; t3.small was used without upgrading.
- The first launched bootstrap stopped before application startup because its checksum selector did not match the release checksum filename format. The instance was terminated. The selector was corrected to support the filename prefix, and the retry reported `docker-compose-linux-x86_64: OK` before executing Compose.
- The default SSM agent reported missing management credentials. No instance role or SSM session was configured or required for this console-driven exercise; no successful SSM access is claimed.

## Reproduction and boundaries

See [the deployment contract](README.md) and [the executed corrected bootstrap](bootstrap.sh). Review permissions, region, resource costs and bootstrap contents before a new run. The bootstrap installs software and schedules shutdown, so it must not run on a personal or shared host. Its pinned source revision remains the same even when newer code is committed. Image tags and dependency ranges are not fully locked, and the legacy Docker builder was used; this is not a production supply-chain design.

The host tested local access to its containers. It did not verify a remote customer path, TLS, Keycloak, Prometheus, continuous CloudWatch collection, CloudWatch alarms, high availability, durable backups or a managed database. Terraform was not applied. Those capabilities must not be inferred from this result.

The pricing API reported USD 0.0216 per t3.small instance-hour in Stockholm. That unit price excludes storage, public IPv4, logs and any other applicable costs. Actual billed charges and consumed credits remain subject to billing updates; the account was not upgraded.

## Independent teardown check

After both the failed and successful runs, DescribeInstances confirmed both hosts terminated. The dedicated security group was deleted. DescribeVolumes and DescribeAddresses returned zero EBS volumes and zero Elastic IP allocations in Stockholm. DescribeLogGroups returned no matching temporary log group. No pre-existing VPC, subnet or default security group was changed. These checks cover the named resource types in the exercise region, not all AWS services globally.
