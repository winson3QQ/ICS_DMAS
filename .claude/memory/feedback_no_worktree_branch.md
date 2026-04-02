---
name: 不要用 worktree 分支 commit
description: commit 應直接在 main 上做，不要透過 worktree 分支再 merge，避免 GitHub 顯示非 main 來源
type: feedback
---

commit 直接在 main 分支上做，不要用 worktree 分支再 fast-forward merge 到 main。

**Why:** GitHub UI 會顯示 `main ← claude/xxx-branch`，使用者希望看到 `main ← main`，保持乾淨的 commit 歷史。

**How to apply:** 如果使用 worktree，在 commit 前先切回 main 分支操作，或直接不使用 worktree。
