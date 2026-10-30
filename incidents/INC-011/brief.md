# INC-011 — Private API is unreachable from an integration

**Status:** offline synthetic scenario and undeployed Terraform scaffold. No AWS packet test, cloud incident, deployment or learner investigation has been performed.

**Synthetic customer complaint:** “Our order integration times out when it connects to the private API. The application team says the API responds on the host. Please investigate before changing access.”

**Severity:** initially unconfirmed. Establish affected integrations, duration, business impact, fallback and data loss before assigning priority. A timeout alone does not establish its cause or severity.

**Environment:** invented same-VPC IPv4 endpoints and `describe-security-groups`-shaped fixtures. The client uses `10.24.1.20` and group `sg-00000000000000001`; the service uses `10.24.2.30` and group `sg-00000000000000002`; the synthetic API listens on TCP 8081 for the purposes of the scenario. These are not observed AWS resources.

## Evidence and reproduction

Use the three commands in the [network lab](../../cloud/aws-network/README.md#analyze-the-snapshots-without-aws). The broken fixture gives `source_egress: match` and `destination_ingress: no_match`. The recovered fixture gives a match in both directions for the intended client. The other client remains a `no_match` negative control. These results are produced from static JSON; they do not show an actual connection attempt or service response.

In a real, authorized sandbox, collect the time, account/region, source and destination network-interface IDs, private IPs, port and exact error. Verify *all* attached groups and their current rules; check the service is listening on the expected private interface. Separately test a connection from the authorized client and inspect route tables, network ACLs and host firewall as needed. Do not publish account identifiers, private snapshots or customer data.

## Hypotheses and investigation

| Hypothesis | Discriminating evidence |
| --- | --- |
| Service ingress does not allow the source group and port | Compare every destination group rule against the observed source groups and port; check client egress. |
| The service is down or bound only to loopback | Inspect the listener and test locally on the destination; a security-group rule cannot fix an absent listener. |
| Network ACL, route, host firewall or an intermediary blocks the path | Inspect the actual packet path and relevant controls; security-group analysis alone cannot rule these out. |
| A different attached group already permits the connection | Check the combined rules across all attached groups before asserting the root cause. |

For the **supplied synthetic snapshot only**, the missing service ingress is the reason the modeled security-group comparison has no match. This conclusion must not be generalized to an uninspected AWS environment.

## Resolution and validation design

The recovered fixture adds a TCP 8081 ingress reference to the intended client group; it does not grant a broad public CIDR. The optional Terraform scaffold represents the same intended configuration with `allow_client_ingress = true`. Its mock tests verify configuration shape only; no real resource or reachability was tested.

For an actual incident, review authorization and blast radius, change only the intended rule, retain a rollback plan, and confirm a fresh end-to-end connection plus an unrelated-client negative control. Confirm all other attached rules and dependencies. AWS security groups are stateful, while network ACLs are stateless; neither eliminates the need to inspect the rest of the path. A rule change may affect every resource attached to that group.

## Example communication

**Initial customer response:** “We are investigating the connectivity failure. We are checking the service and network path and will share an update when we have verified the cause.”

**Resolution wording after actual validation only:** “We identified and corrected the relevant access rule, then verified the affected connection and an unrelated-client control. We will share a further update if monitoring shows a recurrence.”

**Internal handoff:** include time and timezone, affected path, endpoints and all attached group IDs in a restricted channel, port, observed symptoms, tested alternatives, precise change, request or change reference, validation, rollback and remaining uncertainty. Never include credentials.

**Preventive action:** review narrowly scoped network rules as code, add an appropriate regression check and alert on actual end-to-end connectivity. An offline fixture or mock test cannot replace that real verification.
