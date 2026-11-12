# 提示詞規則

這個資料夾是「Claude 要怎麼帶我」的唯一來源。新版 App（`tracker2/app.py`）每次產生提示詞時都會重新讀這些檔案，所以改完存檔就生效，不用重開 App。

| 檔案 | 用在哪裡 | 內容 |
|---|---|---|
| `teach_new.md` | 新課題 | 第一次開始一課時，Claude 的開場方式 |
| `teach_continue.md` | 接續 | 同一課換新對話時，Claude 的開場方式 |
| `teach_common.md` | 新課題、接續 | 帶課的共通規則 |
| `scope.md` | 新課題、接續 | 範圍控制：必學、相關基礎、延伸三類怎麼處理 |
| `kind_register.md` | 暫存器類課題 | 每一步要講清楚的事與範例 |
| `kind_driver.md` | 元件驅動類課題 | 依 datasheet 寫驅動的教法 |
| `kind_arch.md` | 架構與軟體設計類課題 | 先設計介面再實作 |
| `kind_debug.md` | 追蹤與除錯類課題 | 觀察、假設、驗證 |
| `kind_concept.md` | 觀念類課題 | 講清楚、舉例、口頭考 |
| `kind_career.md` | 求職類課題 | Claude 當面試官兼審稿人（不套用其他帶課規則） |
| `kind_prep.md` | 準備類項目 | 逐項確認，不走完整流程 |
| `hal.md` | 暫存器類課題 | HAL 對照的做法與頻率 |
| `wrapup.md` | 技術類課題 | 驗收通過後的收尾總整理（共通部分） |
| `refs.md` | 技術類課題 | 查文件的指路方式、邏輯分析儀 |
| `notes.md` | 全部 | 筆記格式 |
| `style.md` | 全部 | 寫法規則（語言、不用編號指涉） |
| `stuck.md` | 求助 | 卡關時 Claude 的處理方式 |
| `review.md` | 複習 | 已完成課題的口頭測驗：Claude 當面試官出 5 到 8 題，最後給總評與面試卡 |
| `backfill.md` | 補做總整理 | 已完成但沒有總整理筆記的課題：依當時的筆記整理，不重新上課 |

每個課題的類型記在 `learning/progress.json` 的 `kind` 欄位（register、driver、arch、debug、concept、career、prep）。

修改時注意：

- 每個檔案開頭的 `<!-- ... -->` 是給人看的說明，不會放進提示詞。
- 檔案不能是空的，也不要改檔名；改完可以執行 `python tracker2/selftest.py` 檢查。
- 課題資訊、上一課、TODO、筆記標題、程式碼清單由 App 自動帶入，不寫在這裡。
- 補做總整理的提示詞會同時用到 `wrapup.md` 和 `kind_*.md` 最後一段「收尾總整理時另外附上」，這個小標題不要改名。
- App 認得的筆記開頭是【筆記】【問題】【解法】【待解決】【卡關】【本次進度】【待學】【面試】。如果在規則裡新增別的開頭，App 不會自動分類。
