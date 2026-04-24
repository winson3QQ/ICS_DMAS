---
name: C1-B HTTPS 架構決策
description: 全面加密傳輸的架構選擇（nginx、step-ca、CSP、CORS）與業界標準對齊理由
type: project
originSessionId: 063fd0d1-3859-4ef3-9e79-cdaee0d4a13b
---
## C1-B 架構決策（2026-04-24）

### 範圍：Command + Pi 都 HTTPS，但分工不同

- **Command**：nginx 終結 TLS → 反代 FastAPI 127.0.0.1:8000（業界標準，HTTP/2、零中斷 reload、未來 mTLS 一行切）
- **Pi**：Node 內建 `https.createServer` 終結 TLS（Pi 資源緊、單一服務、`server/config.js` 已預埋）

### CORS：env-driven 白名單，不徹底移除

歷史：原 `allow_origins=["*"]` 的 commit 註解寫「允許同區網所有裝置存取」— 是基於「PWA 直接打 Command」的**架構誤解**。實際 PWA→Pi→Command 為 hub-and-spoke，無瀏覽器跨源。

但 §C1-B 規格明文要求「環境變數設定（預設內網網段）」，且未來 TTX Orchestrator（C5-A 獨立服務）+ Tier 3 開放 API（C5-E）會有跨源需求。

決策：保留 middleware，改用 `ALLOWED_ORIGINS` env，預設本機 dev。

### 內網 PKI：step-ca（不用 mkcert / Vault PKI）

- mkcert：22 縣市每台手動 trust 不可行
- HashiCorp Vault PKI：對規模過重
- Let's Encrypt：內網無公網無法 challenge
- step-ca：CNCF landscape，標準 ACME，**per-customer CA 隔離**（每客戶獨立 instance，CA 私鑰外洩只影響該客戶）

mkcert 既有憑證**保留為 fallback**，演練成功一次後再考慮淘汰（時間點：C3-B install.sh 完成）。

### CSP：staged approach（report-only → enforce → strict）

現況：commander_dashboard.html 有 128 個 inline `onclick` + 504 個 `style="..."` + 多處 `<script>` block。

→ C1-B 階段只能寫 basic CSP + `'unsafe-inline'`（妥協現有架構）。
→ C1-F（前端模組化 + esbuild）後升級 nonce-based + strict-dynamic（CSP Level 3）。
→ Report-only 觀察 1-2 週收 violation report 後切 enforce（業界 staged approach，OWASP 認可）。

### nginx 配置模組化 + Tier 3 預留

- `conf.d/ssl-common.conf`：Mozilla Intermediate 2024-09 基線
- `conf.d/security-headers.conf`：HSTS / X-Frame / Referrer-Policy（HSTS 不加 preload，避免內網域名鎖死）
- `conf.d/command.conf`：Command 反代
- `conf.d/tier3-mtls.conf.disabled`：mTLS 雙向憑證（C4 授權重命名啟用）

### 文件位置

- `deploy/README.md` — 統合入口
- `deploy/step-ca/README.md` — PKI 流程
- `deploy/nginx/README.md` — TLS 設定依據

### 啟動腳本

- `start_mac.sh`：HTTP fast path（dev iteration，無 TLS）
- `start_mac_https.sh`：C1-B 完整 stack（step-ca + nginx + FastAPI + Pi TLS）
- `start_pi.sh`：step-ca 優先，mkcert fallback
- `start_windows.bat`：未動（Windows 部署不在 6/30 需求）

### 後續工作（C1-B 範圍外）

- C1-F 前端模組化 → 升級 strict CSP
- C3-B install.sh → 自動 step-ca 部署 + ACME renew timer + nginx reload hook + `STRICT_TLS=true` 強制 Pi 拒絕非 TLS
- C4 授權 → 啟用 `tier3-mtls.conf.disabled`
