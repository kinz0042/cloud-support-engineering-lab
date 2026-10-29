# Support engineer readiness assessment

This assessment is a learning tool. The lab and its automated checks demonstrate a working simulation; they do not establish that its owner independently performed the investigations. Record only work you personally completed.

## Assessment conditions

Use the lab documentation and a running local environment. Do not read the corresponding incident's resolution until you have recorded your hypotheses and evidence. Work without an AI assistant for the timed attempt; use it afterward to review gaps. Never expose actual secrets in evidence.

## Scenario: orders do not reach a customer integration

A customer reports that orders are accepted, but their integration has not received recent notifications. Other customers appear unaffected. You have 45 minutes.

1. Clarify scope, impact, first observed time, and a safe correlation identifier. State what would change your severity assessment.
2. Reproduce using the documented lab setup. Record the order identifier, response status, and timestamps.
3. Inspect application and delivery-worker logs and delivery status. Separate observations from assumptions.
4. List at least three plausible causes and an evidence-based test for each. Consider authentication, customer endpoint failure, and tenant-specific configuration.
5. Identify the cause supported by the available evidence. If evidence is insufficient, say so and identify the next test.
6. Make the smallest appropriate correction, verify delivery, and check for duplicate effects.
7. Write a customer update and a concise internal handoff. Remove credentials and sensitive data.

## Scoring rubric

Score each category 0–2: 0 absent or unsafe; 1 partial; 2 accurate and evidence-backed.

| Category | Full-credit evidence |
| --- | --- |
| Triage | Scope, impact, timing and appropriate severity |
| Reproduction | Clear request, result, identifiers and timestamps |
| Evidence | Relevant logs/status with secrets redacted |
| Hypotheses | Competing explanations and discriminating tests |
| Root cause | Evidence connects cause to symptom; uncertainty acknowledged |
| Resolution | Corrective action appropriate to the cause |
| Validation | Delivery verified and duplicate behavior considered |
| Communication | Clear customer update and actionable engineering handoff |

Target 13/16 with no zero in evidence, root cause or validation. This is a practice benchmark, not an employer certification. Repeat with a different incident before treating it as consistent performance.

## Personal evidence record

- Date and scenario:
- Time taken:
- My observations and commands:
- Hypotheses and tests:
- Root cause and supporting evidence:
- Fix and validation:
- Customer update:
- Score and specific gaps:
- What I would do differently:

Do not publish secrets, customer data, or an AI-generated investigation as your own work.
