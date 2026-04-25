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