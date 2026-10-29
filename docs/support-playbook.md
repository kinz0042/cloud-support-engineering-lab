# Support investigation playbook

This playbook describes how to investigate the lab's synthetic customer reports. It is a guide for repeatable work, not a claim that a real customer incident happened.

## Triage and scope

Record when the issue began, the affected operation, frequency, tenant scope, customer impact and last known success. Establish whether data may be lost or duplicated. Assign severity from actual impact and your team's policy; HTTP 500 alone does not determine severity. Acknowledge the report and set a time for the next update only when you can keep that commitment.

## Gather evidence safely

Record UTC timestamps, environment and build, request method and route, response status, request IDs and redacted logs. Ask for a minimal reproduction. Never ask customers to send passwords, complete API keys, bearer tokens or unredacted sensitive payloads. Check whether the same request behaves differently between tenants, clients or time windows when authorized.

## Investigate

1. State the expected and actual behavior and reproduce it with synthetic data.
2. Trace the request ID through the API logs; compare health, readiness and Prometheus signals.
3. List competing hypotheses, including configuration, credentials, network, data, dependency and product defect. Record what each test proves or rules out.
4. Prefer read-only checks first. If a change is necessary, record a rollback plan and appropriate authorization. In this lab, only modify disposable services and fixtures.
5. Validate the customer workflow, a negative control, and whether queued events were delivered once or safely deduplicated. A green health endpoint or successful order creation alone is insufficient.

## Engineering escalation

Include impact and urgency, start and end times or ongoing status, affected environment and versions, minimal reproducible steps, expected versus actual results, redacted request IDs and logs, hypotheses tested, observed results, workaround and remaining uncertainty. Separate observations from hypotheses; identify any actions already taken and their effects. Link to the exact test run or incident record when available.

## Customer communication

- Initial: acknowledge the impact, explain what is being investigated, and request only information needed.
- Progress: state what has been confirmed, what remains unknown, any safe workaround and when the next update can be expected.
- Resolution: describe the validated outcome in plain language and any customer action needed. Do not state a root cause or promise a permanent fix without evidence.

## Close and prevent recurrence

Write the causal chain supported by evidence, contributing factors, validation, a rollback plan and a specific preventive action with an owner and success condition. If the underlying cause is unknown, say so and track follow-up. The lab's reports distinguish assistant-run synthetic checks from learner investigations; do not present either as production employment.
