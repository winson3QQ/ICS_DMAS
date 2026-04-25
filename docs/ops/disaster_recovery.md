# ICS_DMAS 災害復原 Playbook

> 對應：NIST SP 800-53 CP-2 / CP-9 / CP-10、CIS Controls v8 §11、個資法 §27 安全維護義務、附表十防護基準 §3 營運持續計畫
> 適用版本：cmd-v2.0.6+
> 最後更新：2026-04-25
> Review 週期：每 6 個月一次 + 重大架構變更時

---

## RTO / RPO 承諾

| 指標 | 目標 |
|---|---|
| RTO（Recovery Time Objective）— 恢復時間目標 | ≤ 4 小時 |
| RPO（Recovery Point Objective）— 資料遺失上限 | ≤ 24 小時（單機 SQLite + daily backup）/ ≤ 1 小時（含 NAS rsync） |

**注意**：演練期間（v2.1.0+）若連續寫入頻繁，建議加開 hourly backup（修改 `ics-backup.timer` OnCalendar）。

---

## 自動備份機制

### 部署架構
- **執行**：systemd timer `ics-backup.timer`，每日 03:00 觸發 `ics-backup.service`
- **腳本**：`command-dashboard/scripts/backup_db.py`（呼叫 `services/backup_service.py`）
- **方法**：SQLite online backup API（與 WAL 相容，並發寫入時仍能取得 consistent snapshot）
- **壓縮**：gzip level 6
- **校驗**：sha256
- **原子性**：先寫 `.tmp` 再 rename
- **位置**：`command-dashboard/data/backups/ics-YYYY-MM-DDTHH-MM-SSZ.db.gz`
- **保存**：rolling 30 天（可設定 `--retain-days`）

### 啟用步驟（首次部署 Pi）
```bash
# 1. 複製 systemd unit
sudo cp /home/ics/ics-dmas/systemd/ics-backup.{service,timer} /etc/systemd/system/

# 2. reload + enable timer（service 不需 enable，timer 觸發即可）
sudo systemctl daemon-reload
sudo systemctl enable --now ics-backup.timer

# 3. 驗證 timer 狀態
systemctl list-timers ics-backup.timer
# 預期看到：next 03:00:00；last n/a（首次安裝）
```

### 監控
```bash
# 查 timer 排程
systemctl list-timers ics-backup.timer

# 查最近執行 log
journalctl -u ics-backup.service -n 50 --no-pager

# 查備份清單 + 最新一筆狀態
python /home/ics/ics-dmas/command-dashboard/scripts/backup_db.py --verify-only
```

---

## 還原 Playbook（按情境）

### 情境 A：DB 部分損毀（schema OK，資料可疑）

**症狀**：`/api/health` 200 但前端顯示資料異常 / 計數錯誤 / 報錯。

**步驟**：
1. **暫停寫入**（重要 — 避免覆蓋）：
   ```bash
   sudo systemctl stop ics-command
   ```
2. **備份當前壞檔做 forensic**（不要直接覆寫）：
   ```bash
   cp /home/ics/ics-dmas/command-dashboard/data/ics.db \
      /home/ics/ics-dmas/command-dashboard/data/ics.db.suspect.$(date +%Y%m%dT%H%M%S)
   ```
3. **選最近的好 backup 還原**：
   ```bash
   cd /home/ics/ics-dmas/command-dashboard
   ls -lh data/backups/ | tail -5
   # 選一個 .db.gz
   ```
4. **執行還原**（使用 Python script，內含 verify）：
   ```bash
   python scripts/restore_db.py \
       --backup data/backups/ics-2026-04-25T03-00-00Z.db.gz \
       --target data/ics.db \
       --overwrite
   ```
5. **驗證**：
   ```bash
   python scripts/backup_db.py --verify-only
   sqlite3 data/ics.db "SELECT version, name FROM schema_migrations ORDER BY version;"
   sqlite3 data/ics.db "SELECT COUNT(*) FROM events;"
   ```
6. **重啟服務**：
   ```bash
   sudo systemctl start ics-command
   curl -k https://localhost:8000/api/health
   ```
7. **記錄**（重要 — IR plan 要求）：
   - `audit_log` 寫一筆 `db_restored` 事件（手動或 admin endpoint）
   - 告知所有指揮 / 操作員「資料還原至 YYYY-MM-DD 03:00 狀態」

**RTO 預期**：15-30 分鐘。

---

### 情境 B：DB 完全損毀 / 檔案不見

**症狀**：`ics-command.service` 啟動失敗、SQLite 報 "database is locked" / "file is encrypted or is not a database"。

**步驟**：
1. 同情境 A 步驟 1-2（停服務 + 保留損毀檔）
2. 確認 `data/backups/` 還在（不應損毀因為 backup 是寫入後 atomic rename）
3. 還原最近一筆 backup（見情境 A 步驟 3-5）
4. 重啟服務 + 驗證
5. **聯絡所有 PWA 端**：可能需要重新 sync（Pi → Command 重推 push_queue 內未送資料）

**RTO 預期**：30-60 分鐘。

---

### 情境 C：整台 Pi 損毀（硬體故障）

**症狀**：Pi 無法開機、SSD 無法讀取。

**步驟**：
1. 取備援 Pi（每場演練建議備一台同規格 Pi）
2. SSH 進去：
   ```bash
   ssh ics@備援pi.local
   ```
3. clone repo + 重新設定（參考 `systemd/setup_pi.sh`）：
   ```bash
   git clone https://github.com/winson3QQ/ICS_DMAS.git ~/ics-dmas
   cd ~/ics-dmas/command-dashboard
   bash setup.sh
   ```
4. **如有 NAS rsync backup**：把最新 backup 拉回來：
   ```bash
   rsync -av nas-host:/backups/ics/latest.db.gz data/backups/
   python scripts/restore_db.py --backup data/backups/latest.db.gz --target data/ics.db --overwrite
   ```
5. **如無 NAS backup**：從每 30 分鐘人工 export 的 USB 備份還原（演練前 SOP 應規定）
6. 部署 systemd + 啟服務（參考 `systemd/setup_pi.sh`）
7. 驗證 + 通知所有 PWA 重新連線

**RTO 預期**：2-4 小時（含 setup 時間）。

---

### 情境 D：root CA 損毀（step-ca 私鑰外洩 / 損毀）

**症狀**：信任鏈失效；所有 server cert 變不可信。

**步驟**：
1. **撤銷舊 root CA**（避免他人冒用）— 此操作 **不可逆**：
   ```bash
   bash deploy/step-ca/uninstall-dev.sh   # 移除 trust store
   ```
2. **建新 root CA**：
   ```bash
   bash deploy/step-ca/init-mac-dev.sh    # Mac dev
   # 或 init-customer.sh（C3-B 客戶部署版）
   ```
3. **重發所有 server cert**（command + 各 Pi）：
   ```bash
   bash deploy/step-ca/issue-cert.sh command-host 192.168.100.10
   bash deploy/step-ca/issue-cert.sh shelter-pi  192.168.100.20
   bash deploy/step-ca/issue-cert.sh medical-pi  192.168.100.30
   ```
4. **每個 client 裝置重新匯入 root CA**（iPad / 電腦）
5. **重啟所有服務**

**RTO 預期**：4-8 小時（含每個 client 手動匯入 CA）。

> 預防措施：root CA 私鑰應 **離線保存**（USB + 鎖櫃），平常不放線上。Tier 3 旗艦版的 YubiKey 機制可進一步保護。

---

## Recovery Drill — 每 6 個月

依 NIST CP-4 + CIS §11 要求，**每 6 個月至少跑一次 recovery drill** 並記錄。

### Drill 流程
1. **準備測試環境**（不要在 production Pi 跑）：
   ```bash
   # 用備援 Pi 或 dev VM
   ```
2. **挑情境**（A/B/C/D 輪流，每次選 1-2 個）
3. **執行 playbook 步驟**並計時
4. **驗證恢復後狀態**：
   - schema_migrations 完整
   - events / decisions / accounts 計數合理
   - 所有 PWA 可以連線並 sync
5. **記錄結果**到 `docs/ops/drill_history.md`（如不存在則新建）：
   - 日期 / 主持人 / 情境 / 實際 RTO / 發現問題 / 改善項
6. **改善追蹤**：發現的 gap 開 issue 排進下個 release

### Drill 自動化（未來）
`scripts/recovery_test.sh`（待實作 v2.1.0 第 5 波）：
- 自動建立 staging dir
- 還原最新 backup
- 驗證 schema + 抽樣資料
- 回報 PASS / FAIL

---

## 備份完整性監控

### 日常監控（systemd journal）
```bash
journalctl -u ics-backup.service --since "1 day ago" | grep -E "backup_done|backup_failed"
```

### 異常告警（C3-C 完成後）
- backup 連續 2 天失敗 → 寫 audit_log + 高優先 alert
- backup 檔案大小異常（< 50% 預期） → 警告
- backup 數量 < 預期（30 天應有 30 個） → 警告

### 還原測試自動化（C3-C + C3-D 完成後）
建議每月自動跑 `verify_backup` 對最新 + 隨機抽樣 3 筆 backup，發現損毀立即告警。

---

## Backup 檔案安全性

### 機密性（個資法 §27）
- **目前狀態**：backup 檔案明文 SQLite + gzip — **含 PII 病患資料**
- **風險**：Pi 實體被取得時 backup 與 production 同樣外洩
- **緩解**：
  - 短期：依賴 Pi 實體安全（鎖櫃 + 限定人員）
  - **C1-C 完成後**：DB 內 PII 欄位先經 Fernet 加密 → backup 也是加密狀態
  - **C3-B + LUKS**：磁碟全加密 → backup 也受 OS 層保護
- **NAS rsync 路徑**：必須走 SSH + key auth；NAS 端建議獨立加密 volume

### 完整性
- sha256 校驗每個 backup（記在 systemd log）
- atomic rename → 不會有半寫檔
- gzip 自帶 CRC32 → 損毀時 verify_backup 會 false

### 保存期間
- 30 天 rolling（dev 預設）
- 政府專案建議：90 天 + 重大事件後額外保存 1 年（個資法 §11 + 災害防救法 §41）
- 設定方式：修改 `ics-backup.service` ExecStart 加 `--retain-days 90`

---

## 對應 compliance gap

完成本 playbook + 自動備份 + recovery test 後：
- ✅ G-C01（CP-9 無自動備份）closed
- ✅ G-C02（CP-10 無 DR playbook）closed
- ✅ G-C03（CP-4 無 drill 流程）— 流程文件化 closed；首次 drill 待執行
- ✅ 附表十 §3 營運持續計畫
- ✅ 政府防護基準 §8 業務持續

詳見 [`docs/compliance/matrix.md` Gap Register](../compliance/matrix.md)。

---

## Review History

| 日期 | 版本 | 變更 | 觸發 |
|---|---|---|---|
| 2026-04-25 | v0.1 | 初版（情境 A/B/C/D + drill 流程）| C3-D 實作 |
