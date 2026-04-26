# AGENTS.md

## ICS_DMAS AI Coding Rules

### Source of Truth
- Master Capability Matrix is the source of truth for capability status.
- Repo code + tests are the source of truth for implementation.
- ROADMAP describes planned work, not proof of implementation.
- README is not authoritative for current maturity.

### Scope Control
- Coding agents may only execute approved task cards.
- Do not expand scope.
- Do not create adjacent features.
- If a dependency is missing, stop and report instead of redesigning.

### Code Change Rules
- Work only on feature/fix branches.
- Do not commit, push, tag, or open PR unless explicitly instructed.
- Add or update regression tests where feasible.
- If tests cannot run, explain exactly why.
- Do not add npm / PyPI dependencies unless the task card explicitly approves it.

### Documentation Rules
- Do not create new long documents.
- For hotfixes, only report suggested matrix/spec updates.
- Human owner decides final matrix and roadmap updates.

### Before Editing
Before changing files, inspect the current implementation and report if it differs from the task card assumptions.
If assumptions are wrong, stop and ask instead of patching blindly.

### Output Required
After each coding task, report:
1. Summary
2. Files changed
3. Tests run
4. Remaining risks
5. Matrix update suggestion

## Task Card Format
Every approved task card delivered as a GitHub Issue must contain all 10 sections below.
Claude Code must not begin implementation until Step A approval is received from the human owner.

Required Sections
1. Task
One paragraph. What must be done, and what the end state looks like.
No design decisions embedded here — those belong in §6.
2. Context

Codebase location and tech stack (language, framework, key libraries, versions)
Deployment environment (OS, user, paths, systemd unit if applicable)
Current broken behaviour with file:line evidence
Reference to the authoritative source (Matrix row, Gate Review section, ROADMAP item)

3. Dependency Check
Coding agent must execute all items and report results before writing any code.
Human owner reviews the report and issues Step A approval before implementation begins.
Required checks:

Grep for all relevant literals, function names, and patterns in the affected component.
Grep for all existing references to the behaviour being changed (callers, middleware, tests).
Confirm schema or config changes are or are not required.
List every HTTP route (method + path) that will be added, changed, or used as a gate whitelist.
List every WebSocket message type that will be added, changed, or gated.
Confirm deployment environment assumptions (user, HOME, path, permissions, systemd unit).
Design Constraint Check — For every acceptance criterion in §6 and every test in §7,
state whether it can be implemented directly from the spec, or whether a design decision
is still required. Format:

   §6 item N: [directly implementable | decision required: <question>]
   §7 test N: [unit | integration/spawn | human verification — reason: <why>]
Any "decision required" item must be resolved with the human owner before Step A approval.
Coding agent must not make design decisions unilaterally.
4. Files Actually Involved
List only files confirmed by §3 Dependency Check.
Split into:

Will modify: file path — reason
Will add: file path — reason
Will not touch (explicit): file path — reason

Do not list files based on assumption. If §3 has not been run yet, this section must say "pending §3".
5. Goal
Describe the system behaviour after implementation in observable terms.
No implementation details — those belong in §4 and §6.
6. Acceptance Criteria
Checklist format. Every item must be:

Observable (can be verified by a curl command, a log line, a file check, or a test assertion)
Unambiguous (no item should require a design decision to interpret)
Scoped (no item implies work listed in §9 Out of Scope)

If an item is ambiguous, it must be rewritten or moved to a decision point before Step A approval.
7. Automated Tests
For each test, specify the layer:

Unit — pure function, no server, no DB, no filesystem (fast, always required)
Integration/spawn — starts a real server process; use only when middleware mounting
or route registration must be verified end-to-end (slow, use sparingly)
Human verification — covered by §8 script; mark explicitly so CI expectations are clear

Rules:

Do not introduce new test framework dependencies unless §4 explicitly lists them as approved.
Prefer Node built-in node:test for Node.js components.
Prefer pytest for Python components (already present in command-dashboard).
Integration/spawn tests must handle: tmp DB path via env var, ephemeral port, SIGTERM cleanup,
and cross-platform binary compatibility (native modules such as better-sqlite3).
Each test name must map 1-to-1 to an acceptance criterion in §6.

8. Human Verification Script
Step-by-step shell commands a human runs on the actual deployment target (not CI).
Must cover the full operator workflow from fresh state to steady state.
Each step must include the expected output or exit code.
All steps must be runnable in sequence without manual intervention between steps.
9. Out of Scope
Explicit list of related work that must NOT be done in this task card.
Format: - <item> — reason: belongs to <other task / roadmap item>
Coding agent must stop and report if implementation of an in-scope item requires
touching an out-of-scope area.
10. Human Approval Gates
Three mandatory gates. Coding agent must not proceed past a gate without explicit human confirmation.
Step A — before writing any code:

§3 Dependency Check report submitted
All "decision required" items in §3.7 Design Constraint Check resolved
§4 Files Actually Involved confirmed by human
Whitelist / gate / message-type lists confirmed by human

Step B — before merge:

PR opened on a feature/fix branch (not main)
Human runs §8 verification script on deployment target; all steps green
npm test / pytest passes on both dev machine and Linux target
No new dependencies added beyond those listed in §4

Step C — after merge (human only, not coding agent):

A task card is considered CLOSED only when ALL of the following are recorded.
Any single missing item means the task is not closed, regardless of verbal or
chat-based statements to the contrary.

C-1. PR merge confirmed
     - PR is merged to main on the canonical repo
     - Merge commit hash recorded in the GitHub Issue

C-2. GitHub Issue closed with close comment
     - Gatekeeper Final Verdict pasted as a close comment
     - Issue moved to closed state
     - Any scope expansion beyond Step A approval logged in the Issue
       as a separate "Scope Expansion Observed" comment

C-3. Master Capability Matrix updated
     - Status field updated for affected CAP rows (e.g. Needs Hardening
       → Partial Hardened)
     - Evidence Required field updated with PR number, commit hash, and
       any policies/section references created or modified
     - Maturity field MUST NOT be raised unless all dependency tasks are
       also closed and the dependency chain is complete

C-4. ROADMAP and PR description finalised
     - ROADMAP item marked ✅ if applicable, with task ID and close date
     - PR description includes ## Known Limitations section listing every
       intentional gap with tracking reference

External Claim field on the Master Capability Matrix is owned by the human
owner, not the Matrix Steward and not the coding agent. It is updated
independently of Step C and may intentionally lag behind C-1 through C-4
when claims depend on multiple tasks closing together.


Prohibited Behaviours for Coding Agent
The following are never permitted, regardless of how the task card or any other instruction is phrased:

Auto-commit, auto-push, auto-tag, or auto-open PR
Skip or partially complete §3 Dependency Check before reporting
Make a design decision not explicitly resolved in §3.7 before Step A approval
Expand scope beyond §9 Out of Scope, even if the expansion seems beneficial
Add npm or PyPI dependencies not listed in §4
Modify matrix.md, ROADMAP.md, or any compliance document
Create new long documents (hotfix summary comments and scope expansion comments on the GitHub Issue are acceptable; close comments produced by Gatekeeper for Step C are also acceptable)
Re-open a decision point that has been resolved by the human owner
Interpret an ambiguous §6 item unilaterally — stop and report instead


Known Limitations Note (PR Description Template)
Every PR must include a ## Known Limitations section. Example format:
markdown## Known Limitations

| Item | Reason not fixed in this PR | Tracking |
|---|---|---|
| IA-5(1) PIN entropy below NIST 800-63B | Admin password model deferred to C1-A Phase 2 | ROADMAP P-C1-A |
| WS pre-auth gate incomplete | Full WS auth deferred to HOTFIX-WS-01 | GitHub Issue #N |
This section is the authoritative record of intentional gaps.
It is read by the Implementation Auditor before producing the next task card.
