# STM32 暫存器韌體學習（2 個月衝刺）

STM32F103C8T6 從 HAL 改用暫存器重做的學習紀錄，最終作品為「姿態感測資料記錄器」。

- 📒 [學習進度與筆記](learning/README.md)
- ❓ [問題整理（複習用）](learning/QUESTIONS.md)
- 💾 各課題程式碼：`projects/SPRINT-Wxx-Sxx/`

## 資料夾結構

```
CLAUDE.md            給 Claude 的背景說明（Claude Code 會自動讀取）
啟動App.bat          雙擊開啟學習進度 App
tracker/             學習進度 App（只用 Python 標準函式庫）
learning/
  progress.json      所有課題、狀態、筆記（App 的資料）
  README.md          進度總覽（自動產生）
  QUESTIONS.md       問題整理（自動產生）
  notes/             每個課題的筆記頁（自動產生）
projects/
  SPRINT-W01-S03/    該課題的程式碼（例如 CubeIDE 專案）
```

## 使用學習進度 App

需要：Python 3.8 以上、Git。

1. 雙擊 `啟動App.bat`（或在這個資料夾執行 `python tracker/app.py`），瀏覽器會自動開啟。
2. 在任務列表按「開始」→ 計時開始，狀態變成「進行中」。
3. 過程中隨時記下「問題／筆記／解法」（Ctrl + Enter 儲存）。
4. 程式碼：
   - 按「開啟資料夾」直接在 `projects/<課題代碼>/` 建立 CubeIDE 專案，或
   - 用「上傳檔案」「上傳整個資料夾」或拖曳，把程式碼放進該課題資料夾（`Debug/`、`.o`、`.elf` 等會自動略過）。
5. 按「結束本次課題」：選擇已完成、下次繼續或卡關 → 自動 commit 筆記與程式碼；完成時加上 tag（例如 `SPRINT-W01-S03`），並 push 到 GitHub。
6. 換電腦時先按「⟳ 同步」（App 啟動時也會自動同步）。

自己 commit 程式碼時，在訊息裡寫上課題代碼（例如 `SPRINT-W02-S04: 加入 ORE 處理`），App 的任務詳細頁就會列出這些 commit，並連到 GitHub。

## 在其他裝置複習

push 到 GitHub 後，用手機或任何電腦打開 repo 的 `learning/README.md` 或 `learning/QUESTIONS.md` 就能閱讀所有筆記。
