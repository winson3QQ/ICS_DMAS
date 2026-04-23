# ICS DMAS 測試目錄

> 目前共 **133 個測試案例**，分三層執行。  
> 執行指令：`bash scripts/run_tests.sh`

---

## 測試分層說明

| 層 | 目的 | 特性 |
|----|------|------|
| **Unit** | 測單一函式的輸入輸出 | 不碰 DB、不起 server、最快 |
| **Integration** | 測模組之間的協作，包含真實 DB 操作 | 每個測試用獨立的暫存 SQLite |
| **API** | 模擬 HTTP 請求，測完整的請求→回應流程 | 透過 FastAPI TestClient，不需要起真正的 server |

---

## Unit 測試（39 個）

### `test_helpers.py` — 基礎工具函式

| 測試案例 | 驗證什麼 |
|---------|---------|
| `test_correct_pin_verifies` | 用正確 PIN 驗證，應該通過 |
| `test_wrong_pin_fails` | 用錯誤 PIN 驗證，應該失敗 |
| `test_same_pin_different_salt` | 同一個 PIN 兩次加密，因為 salt 不同所以 hash 也不同（防彩虹表） |
| `test_deterministic_with_same_salt` | 固定 salt 下，同一 PIN 的 hash 結果一致（可重現驗證） |
| `test_empty_pin` | 空字串 PIN 也能正常加密與驗證，不會 crash |
| `test_returns_iso_format` | `now_utc()` 回傳的時間格式是 ISO 8601（含 T 和 Z） |
| `test_monotonic` | 連續呼叫 `now_utc()`，後者一定 ≥ 前者（時間不倒流） |
| `test_none_returns_none` | `iso_utc(None)` 安全地回傳 None，不 crash |
| `test_valid_iso_passthrough` | 已是正確格式的時間字串直接通過 |
| `test_invalid_returns_original` | 格式錯誤的字串不 crash，容錯處理 |
| `test_adds_positive_minutes` | `add_minutes("10:00", 30)` → "10:30" |
| `test_adds_zero_minutes` | 加 0 分鐘，時間不變 |
| `test_crosses_hour_boundary` | 10:45 + 20 分鐘 = 11:05（跨小時正確計算） |

---

### `test_calc_engine.py` — 計算引擎（規格 6.x）

| 測試案例 | 驗證什麼 |
|---------|---------|
| `test_recent_is_ok` | 1 分鐘前的快照，新鮮度應為「ok」 |
| `test_warn_boundary` | 7 分鐘前的快照，應為「warn」或更嚴重 |
| `test_crit_boundary` | 16 分鐘前的快照，應為「crit」或「lkp」 |
| `test_lkp_very_old` | 30 分鐘前的快照，必定是「LKP（最後已知位置）」 |
| `test_minutes_field_is_positive` | 新鮮度結果的 `minutes` 欄位必須是正數 |
| `test_invalid_time_returns_lkp` | 時間格式錯誤時，安全地回傳 lkp，不 crash |
| `test_no_data_returns_zero` | 四個節點都沒資料時，MPI（醫療壓力指數）= 0 |
| `test_full_beds_raises_pressure` | 20 床占了 19 床且有 10 人等待，MPI 應 > 5（高壓） |
| `test_empty_beds_no_waiting` | 沒人用床也沒人等待，MPI = 0 |
| `test_components_present` | MPI 結果必須包含 `components` 分解欄位 |
| `test_forward_casualties_add_pressure` | 前進組 5 名紅傷患 × 0.8 = 4.0 壓力分 |
| `test_insufficient_data` | 沒有快照時，趨勢信心度為「insufficient」，rate 為 None |
| `test_upward_trend` | 10 分鐘內床位從 5 增到 15，方向應為「up」 |
| `test_flat_trend` | 10 分鐘內床位不變，方向應為「flat」 |
| `test_recent_minutes_ago` | `minutes_ago()` 對 5 分鐘前的時間應回傳 4.5～5.5 |
| `test_invalid_returns_999` | 格式錯誤時回傳 999.0，代表「未知/極舊」 |

---

### `test_auth_service.py` — Session 管理

| 測試案例 | 驗證什麼 |
|---------|---------|
| `test_returns_uuid_string` | `create_session()` 回傳 36 字元的 UUID 字串 |
| `test_session_stored` | 建立後，session 真的存在 in-memory store 裡 |
| `test_unique_tokens` | 兩次 `create_session()` 產生不同的 token |
| `test_valid_token` | 有效 token 可以取回 session 資料 |
| `test_invalid_token` | 不存在的 token 回傳 None |
| `test_expired_session` | 已過期的 session 被清除並回傳 None |
| `test_removes_session` | `destroy_session()` 真的把 session 從 store 移除 |
| `test_nonexistent_returns_none` | 對不存在的 token 呼叫 destroy 不 crash |
| `test_fresh_session_has_remaining` | 剛建立的 session，remaining 秒數 > 0 |
| `test_nonexistent_returns_zero` | 不存在的 token 的 remaining = 0 |

---

## Integration 測試（36 個）

> 每個測試使用獨立的 SQLite 暫存檔，測試結束自動刪除，互不影響。

### `test_account_repo.py` — 帳號管理

| 測試案例 | 驗證什麼 |
|---------|---------|
| `test_create_and_retrieve` | 建帳號後可以查到，欄位正確 |
| `test_duplicate_username_raises` | 重複的帳號名稱應拋出例外 |
| `test_pin_not_stored_in_plaintext` | DB 裡的 pin_hash 不是明文（安全性驗證） |
| `test_correct_credentials` | 正確帳密，`verify_login()` 回傳帳號資料 |
| `test_wrong_pin` | 錯誤 PIN，`verify_login()` 回傳 None |
| `test_nonexistent_user` | 不存在的帳號，`verify_login()` 回傳 None |
| `test_pin_not_in_response` | 登入成功的回傳值不包含 `pin_hash`、`pin_salt`（不洩漏機敏資料） |
| `test_creates_admin_if_empty` | 第一次啟動，自動建立 admin 帳號 |
| `test_idempotent` | 呼叫兩次 `ensure_default_admin()` 不會建出兩個 admin |
| `test_default_pin_works` | 預設 admin 帳號的 PIN 是「1234」，可以登入 |
| `test_suspend_and_login_fails` | 停用帳號後，即使密碼正確也無法登入 |

---

### `test_exercise_repo.py` — 演練場次

| 測試案例 | 驗證什麼 |
|---------|---------|
| `test_basic_create` | 建演練後，id 存在，status 為「setup」 |
| `test_defaults` | 新建演練的 mutex_locked=0、ended_at=null |
| `test_get_exercise` | 用 id 可以查到正確的演練 |
| `test_list_exercises` | 建兩個演練後，列表長度 ≥ 2 |
| `test_activate_sets_status` | 啟動後 status=active、mutex_locked=1、started_at 有值 |
| `test_only_one_active_allowed` | 已有一個 active，再啟動第二個應拋出例外（mutex） |
| `test_get_active_exercise` | `get_active_exercise()` 回傳正確的進行中演練 |
| `test_archive_releases_mutex` | 歸檔後 status=archived、mutex_locked=0、ended_at 有值 |
| `test_can_activate_new_after_archive` | 舊演練歸檔後，可以啟動新的（mutex 釋放） |

---

### `test_event_repo.py` — 事件管理

| 測試案例 | 驗證什麼 |
|---------|---------|
| `test_creates_with_code` | 建事件後，event_code 以「EV-」開頭 |
| `test_code_sequential` | 第二個事件的序號大於第一個（遞增不重複） |
| `test_status_defaults_to_open` | 新建事件的 status 預設為「open」 |
| `test_with_exercise_id` | 指定 exercise_id 的事件，用該 ID 查詢時查得到 |
| `test_open_to_in_progress` | 事件可以從「open」轉為「in_progress」 |
| `test_in_progress_to_resolved` | 事件可以從「in_progress」轉為「resolved」 |
| `test_open_to_resolved_directly` | 事件可以從「open」直接轉為「resolved」 |
| `test_filter_by_status` | `get_events(status=...)` 只回傳指定狀態的事件 |
| `test_note_appended` | 新增筆記後，事件的 notes 欄位包含該筆記內容 |

---

### `test_decision_repo.py` — 決策管理

| 測試案例 | 驗證什麼 |
|---------|---------|
| `test_basic_create` | 建決策後，status 預設為「pending」 |
| `test_with_primary_event` | 決策可以關聯到特定事件，查詢時 primary_event_id 正確 |
| `test_approve_decision` | 指揮官核准後，status=approved、decided_by 有值 |
| `test_hold_decision` | 指揮官暫緩後，status=hold |
| `test_nonexistent_raises` | 對不存在的決策執行 decide，應拋出例外 |
| `test_list_decisions` | 建兩個決策後，列表長度 ≥ 2 |
| `test_filter_by_exercise` | 只回傳屬於特定演練的決策 |

---

## API 測試（58 個）

> 透過 FastAPI TestClient，模擬完整的 HTTP 請求→認證→邏輯→回應流程。

### `test_auth_api.py` — 認證流程

| 測試案例 | 驗證什麼 |
|---------|---------|
| `test_success` | 正確帳密，HTTP 200，回傳 session_id |
| `test_wrong_pin` | 錯誤 PIN，HTTP 401 |
| `test_nonexistent_user` | 不存在的帳號，HTTP 401 |
| `test_missing_fields_422` | 缺少 pin 欄位，HTTP 422（格式錯誤） |
| `test_no_token_returns_401` | 沒帶 X-Session-Token，HTTP 401 |
| `test_invalid_token_returns_401` | 帶假的 token，HTTP 401 |
| `test_valid_token_passes` | 帶有效 token，HTTP 200 |
| `test_returns_remaining` | Heartbeat 回傳 remaining 秒數 > 0 |
| `test_without_token_401` | Heartbeat 沒帶 token，HTTP 401 |
| `test_returns_user_info` | `/api/auth/me` 回傳 username、role，不含 pin_hash |
| `test_logout_invalidates_session` | Logout 後，同一 token 再請求應收到 401 |

---

### `test_events_api.py` — 事件管理 API

| 測試案例 | 驗證什麼 |
|---------|---------|
| `test_success` | 正確欄位建事件，回傳 event_code |
| `test_invalid_severity_422` | severity 填「high」（不合法），HTTP 422 |
| `test_invalid_unit_422` | reported_by_unit 填未知單位，HTTP 422 |
| `test_missing_operator_name_422` | 缺少 operator_name，HTTP 422 |
| `test_with_exercise_id` | 帶 exercise_id 建事件，HTTP 200 |
| `test_empty` | 還沒建事件時，列表回傳空陣列 |
| `test_after_create` | 建事件後，列表長度 ≥ 1 |
| `test_filter_by_status` | `?status=open` 只回傳 open 的事件 |
| `test_in_progress` | 把事件狀態改為 in_progress，HTTP 200 |
| `test_resolve` | 經由 in_progress 轉到 resolved，HTTP 200 |
| `test_nonexistent_event_returns_4xx` | 對不存在的事件改狀態，HTTP 4xx |
| `test_add_note` | 對事件新增筆記，HTTP 200 |

---

### `test_exercises_api.py` — 演練管理 API

| 測試案例 | 驗證什麼 |
|---------|---------|
| `test_empty_list` | 還沒建演練時，列表為空陣列 |
| `test_after_create` | 建演練後，列表長度為 1 |
| `test_minimal_fields` | 只帶 name + type，HTTP 200，status 為 setup |
| `test_with_all_fields` | 所有欄位都帶，location 欄位正確儲存 |
| `test_missing_name_422` | 缺少 name，HTTP 422 |
| `test_activate` | 啟動演練，HTTP 200，status 變 active |
| `test_mutex_second_activate_fails` | 已有 active 演練，再啟動第二個應 HTTP 409 |
| `test_nonexistent_exercise_404` | 啟動不存在的演練 ID，HTTP 404 |
| `test_archive_after_active` | 歸檔已啟動的演練，HTTP 200，status 變 archived |
| `test_can_activate_after_archive` | 歸檔後可以啟動新演練，HTTP 200 |
| `test_create_aar` | 建 AAR 紀錄，HTTP 200，有 id |
| `test_list_aar` | 建兩筆 AAR 後，列表長度為 2 |

---

### `test_pi_push_api.py` — Pi 節點推送 API（13 個）

| 測試案例 | 驗證什麼 |
|---------|---------|
| `test_shelter_heartbeat` | shelter 空推送（心跳），HTTP 200，ok=true |
| `test_medical_heartbeat` | medical 空推送（心跳），HTTP 200 |
| `test_no_bearer_returns_401` | 沒帶 Authorization header，HTTP 401 |
| `test_wrong_token_returns_403` | 錯誤的 Bearer token，HTTP 403 |
| `test_unknown_unit_returns_403` | 未知 unit_id，HTTP 403 |
| `test_cross_unit_token_rejected` | shelter token 推送 medical，HTTP 403（跨節點不可用） |
| `test_push_returns_ok` | shelter 推 persons + beds + resources，HTTP 200，records_count 正確 |
| `test_push_stores_batch` | 推送後 `/api/pi-data/shelter/list` 回傳正確筆數 |
| `test_push_groups_by_table` | grouped 欄位依 table_name 分組，persons/beds 各 2 筆 |
| `test_push_returns_ok` (medical) | medical 推 patients + resources + incidents，HTTP 200 |
| `test_push_stores_batch` (medical) | 推送後 `/api/pi-data/medical/list` offline=false |
| `test_offline_before_push` | 推送前查詢 offline=true |
| `test_two_nodes_push_independently` | shelter + medical 各自推送，資料不互相干擾 |

---

### `test_dashboard_api.py` — Dashboard 聚合驗證（10 個）

| 測試案例 | 驗證什麼 |
|---------|---------|
| `test_returns_200` | `/api/dashboard` HTTP 200 |
| `test_pi_nodes_empty_before_registration` | 未建節點時 pi_nodes 為空陣列 |
| `test_no_auth_returns_401` | 未帶 token，HTTP 401 |
| `test_pi_node_appears_after_push` | shelter 推送後 pi_nodes 列表出現 shelter |
| `test_shelter_bed_used` | 2 人已安置 → shelter_history[0].bed_used = 2 |
| `test_shelter_pending_intake` | 1 人等候中 → shelter_history[0].pending_intake = 1 |
| `test_medical_red_casualties` | 1 位紅傷患在場 → medical_history[0].casualties_red = 1 |
| `test_medical_excludes_discharged` | 已離區傷患不計入 bed_used（3 人中 1 已離，bed_used=2） |
| `test_both_nodes_in_pi_nodes_list` | shelter + medical 同時推送，pi_nodes 包含兩者 |
| `test_both_histories_populated` | 兩節點推送後，shelter_history 和 medical_history 都有資料 |

---

## 目前未覆蓋的範圍

| 模組 | 覆蓋率 | 原因 | 預計在 |
|------|--------|------|--------|
| `routers/ttx.py` | 25% | TTX 場景注入流程複雜 | C2 |
| `services/ai_service.py` | 36% | AI stub，Wave 5 才實裝 | Wave 5 |
| `routers/sync.py` | — | 三 Pass 同步邏輯需要完整情境 | C2 |
| `routers/map.py` | — | 需要實際的 MBTiles 檔案 | C2 |

---

## 如何新增測試

1. 在對應的層（unit/integration/api）建立新的 `test_XXX.py`
2. 在測試檔開頭加 `pytestmark = pytest.mark.unit`（或 integration/api）
3. 執行 `bash scripts/run_tests.sh unit` 確認通過
4. 完整跑 `bash scripts/run_tests.sh` 確保沒有回歸
