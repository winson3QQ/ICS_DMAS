---
name: AI Task Card
about: Approved task card for Codex / Claude Code implementation
title: "[AI Task] "
labels: ai-candidate, needs-human-approval
assignees: ""
---

# AI Task Card

## Capability

<!--
Which capability from the Master Capability Matrix does this task affect?
Example: Pi / WebSocket Sync, Trusted Ingest, AAR Timeline
-->

-

## Source

<!--
Reference existing sources. Do not create new docs.
-->

- Master Capability Matrix row:
- Security review:
- Roadmap / cX item:
- Related issue / PR:

## Goal

<!--
One sentence. What should be true after this task is completed?
-->

-

## Dependency Check

<!--
This section should be produced by Matrix Steward / Implementation Auditor before Codex or Claude Code starts.
-->

- Required predecessors:
- Hard blockers:
- Soft blockers:
- Explicitly out of scope:
- If dependency is missing, coding agent must:

## Implementation Reality Check

<!--
This section must be filled before implementation.
Do not produce coding work without code reality check.
-->

- Checked files:
  - 
- Observed current behavior:
  - 
- Document / Matrix mismatch:
  - 
- Existing tests:
  - 
- Hidden dependencies:
  - 
- Conclusion:
  - [ ] Safe to implement
  - [ ] Not safe; needs human clarification first

## Acceptance Criteria

<!--
Concrete, testable criteria. No vague "improve security" wording.
-->

- [ ] AC1:
- [ ] AC2:
- [ ] AC3:

## Automated Tests

<!--
What automated tests should be added or updated?
If no test framework exists, say so and provide smoke/manual fallback.
-->

- [ ] Test 1:
- [ ] Test 2:
- [ ] Existing relevant tests run:

## Human Verification Script

<!--
Human owner must run this before merge or maturity upgrade.
-->

1.
2.
3.
4.
5.

Expected result:

-

## Out of Scope

<!--
Prevent coding agent from expanding scope.
-->

- 
- 
- 

## Human Gates

- [ ] Gate A: Scope approved by human owner
- [ ] Gate B: Task card approved by human owner
- [ ] Gate C: Diff reviewed by human owner
- [ ] Gate D: Auditor review passed
- [ ] Gate E: Security final gate passed
- [ ] Gate F: Human verification passed
- [ ] Gate G: Matrix update decided

## Coding Agent Instructions

Codex / Claude Code must follow these rules:

- Execute only this approved task card.
- Do not expand scope.
- Do not create adjacent features.
- Do not create long documents.
- Do not add npm / PyPI dependencies unless explicitly approved.
- If implementation differs from task assumptions, stop and report.
- Add or update regression tests where feasible.
- If tests cannot run, explain exactly why.
- Do not merge to main.

## Required Output From Coding Agent

After implementation, report:

1. Summary
2. Files changed
3. Tests run
4. Remaining risks
5. Matrix update suggestion
