---
name: Git push 需經確認
description: commit 後停在本地，不自動 push，需使用者確認後才 push
type: feedback
---

commit 完成後，不自動執行 git push。停下來，等使用者確認再 push。

**Why:** push 影響遠端共享狀態，使用者可能想先在本地審查 diff 或累積多個 commit 再一起推。
**How to apply:** 除非使用者明確說「push」或「推上去」，否則 commit 後只回報本地狀態，不執行 push。
