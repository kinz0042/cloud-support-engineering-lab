# Live private-network investigation — 30 October 2026

Assistant-executed AWS exercise in Stockholm (`eu-north-1`), not a customer outage or independent learner investigation. The Terraform module was not applied: AWS Core called EC2 APIs directly.

## Environment and complaint

Synthetic complaint: “The service is running, but our integration cannot connect.”

Two Amazon Linux 2023 t3.micro instances occupied the same existing VPC and subnet. Each had one dedicated lab security group, an encrypted 8 GiB gp3 root disk with DeleteOnTermination, IMDSv2 required, no public IPv4 address, no supplied SSH key and no instance role. CPU credit mode was standard. The service served a synthetic file on TCP 8081; the client made bounded curl probes to its private IP. No packages were downloaded and no NAT gateway, load balancer or public endpoint was created. Both bootstraps scheduled shutdown after 20 minutes, with instance-initiated shutdown configured to terminate.

## Evidence and investigation

The service console output contained its loopback response `synthetic-network-ok` and `CSELAB_SERVICE_READY`. The client console reported:

```text
CSELAB_PROBE attempt=1 curl_exit=28 body=
CSELAB_PROBE attempt=8 curl_exit=28 body=
CSELAB_PROBE attempt=9 curl_exit=0 body=synthetic-network-ok
CSELAB_PROBE attempt=10 curl_exit=0 body=synthetic-network-ok
CSELAB_PROBE attempt=11 curl_exit=0 body=synthetic-network-ok
```

These are actual selected console lines, with host and resource identifiers omitted. The recovery output was retrieved at 19:55:07 UTC. Console output was delayed and sometimes duplicated by cloud-init; duplicate lines are not counted as separate probes. Curl exit 28 indicates timeout, not an HTTP status or a unique network root cause.

DescribeSecurityGroups showed client egress allowed only TCP 8081 to the service security group. The service group had no ingress and no outbound rules. DescribeInstances confirmed neither instance had a public IP. Local service success ruled out a completely absent listener at that moment; direct private-IP probes did not involve DNS or TLS.

## Cause, fix and validation

The controlled missing configuration was the service's ingress rule. AuthorizeSecurityGroupIngress added exactly TCP 8081 from the client security group. No CIDR-wide or public ingress was added. Subsequent client probes succeeded and returned the known synthetic body while the application was unchanged.

Competing hypotheses included listener failure, wrong destination/port, route or ACL restrictions, and security-group mismatch. This before/after result supports the missing service ingress rule as the cause of the synthetic failure. It is not a complete audit of routes, ACLs, host configuration or arbitrary other traffic. No third-client negative control, packet capture or Reachability Analyzer run was performed. The existing offline inspector remains a rule comparison tool, not a packet test.

## Reproduction outline

Use only authorized disposable resources and an allowed region. Boot a private client and a small service; verify the service locally and collect the client's timeout. Inspect all security groups attached to both interfaces. Start with scoped client egress and absent service ingress, then add only the peer-group/port ingress rule. Repeat new connections and compare response content. Do not modify a shared default group. The service bootstrap and a sanitized client template are saved beside this record. The client template replaces the historical private IP with a required SERVICE_PRIVATE_IP input; configure it with the new lab service address before deployment.

## Cleanup verified

TerminateInstances was followed by DescribeInstances: both instances were terminated. DescribeVolumes returned zero volumes in Stockholm. The client-to-service egress reference was removed, both lab groups were deleted, and DescribeSecurityGroups returned only the pre-existing default group. The existing VPC, subnets and default security group were left unchanged.

## Cost and limits

The pricing API returned an on-demand Linux t3.micro rate of USD 0.0108 per instance-hour for Stockholm on the exercise date. That is a compute unit price, not the full exercise cost: EBS and any other applicable charges are separate. Actual billed usage/credit consumption was not yet verified. No reservation or paid plan upgrade was purchased. The lab's overall target remains USD 10 of credit; budget email delivery remains unresolved.

This proves one live, synthetic EC2 security-group recovery and cleanup. It does not claim that RelayDesk was deployed on EC2, that the Terraform scaffold provisions this entire environment, or that the learner independently diagnosed it.

## Example customer update

“We confirmed the test service was responding locally and identified a missing inbound rule for the integration client. We added only the required client-group access to the service port and verified successful responses from that client. The temporary test resources were then removed.”
