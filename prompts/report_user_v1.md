# Task

Generate the final structured diagnostic report.

## Required JSON Shape

Return exactly this shape:

{{"title":"...","impact":"...","likely_root_cause":"...","evidence":["..."],"recommended_actions":["..."],"confidence":"medium"}}

## Incident Input

user_request:
{user_request}

## Evidence From Topology Worker

impact_summary:
{impact_summary}

## Evidence From Memory Worker

memory_summary:
{memory_summary}

## Optional Simulated Repair Context

fix_plan:
{fix_plan}

fix_execution_result:
{fix_execution_result}

operator_feedback:
{operator_feedback}

## Report Requirements

- Base the report only on the evidence above.
- If evidence is incomplete, use `confidence` = `low` or `medium`.
- Include 3 to 6 evidence bullets.
- Include 3 to 6 recommended actions.
- Return only valid JSON.
