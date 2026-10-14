# STM32 暫存器韌體學習（2 個月衝刺）

STM32F103C8T6 從 HAL 改用暫存器重做的學習紀錄，最終作品為「姿態感測資料記錄器」。

- 📒 [學習進度與筆記](learning/README.md)
- ❓ [問題整理（複習用）](learning/QUESTIONS.md)
- 💾 各課題程式碼：`projects/SPRINT-Wxx-Sxx/`

## 資料夾結構

```
CLAUDE.md            給 Claude 的背景說明（Claude Code 會自動讀取）
STM32Tracker.exe     雙擊開啟學習進度 App（不會出現終端機視窗）
tracker/             學習進度 App（只用 Python 標準函式庫）
  launcher.cs        STM32Tracker.exe 的原始碼
  build_exe.bat      重新編譯 exe（只有改 launcher.cs 才需要）
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

1. 雙擊 `STM32Tracker.exe`，會開啟一個獨立的 App 視窗（用 Windows 內建的 Edge App 模式，沒有網址列與分頁；背景程式不會出現終端機視窗）。
   - 關閉視窗後，App 會在幾秒內自動結束；也可以按右上角的「關閉 App」。
   - 視窗大小與位置會被記住；GitHub 連結會用你平常的瀏覽器開啟。
   - 如果 exe 不見了，雙擊 `tracker/build_exe.bat` 重新產生（用 Windows 內建的 C# 編譯器，不需要網路）。
   - 發生錯誤時會跳出對話框，紀錄在 `tracker/app.log`。
2. 在任務列表按「開始」（做過的課題顯示「繼續」）→ 狀態變成「進行中」，並跳出**開始提示詞**：複製後貼到 Claude，Claude 會依完成標準一步一步帶你（之後可在進行中的卡片按「📋 開始提示詞」再取得）。
3. 過程中隨時記下「問題／筆記／解法」（Ctrl + Enter 儲存）。卡住時按「🆘 求助提示詞」，描述卡在哪裡，App 會附上課題資訊、筆記與程式碼產生求助提示詞。
4. 程式碼：
   - 按「開啟資料夾」直接在 `projects/<課題代碼>/` 建立 CubeIDE 專案，或
   - 用「上傳檔案」「上傳整個資料夾」或拖曳，把程式碼放進該課題資料夾（`Debug/`、`.o`、`.elf` 等會自動略過）。
5. 按「結束本次課題」→ 自動 commit 筆記與程式碼並 push 到 GitHub：
   - **已完成**：總結寫入課題，加上 tag（例如 `SPRINT-W01-S03`）。
   - **尚未完成**：本次進度記成一則【本次進度】筆記，下次的開始提示詞會帶上它；不打 tag。
   - **卡關**：必須描述卡在哪裡，記成一則未解決的【卡關】問題，並跳出求助提示詞。
6. 換電腦時先按「⟳ 同步」（App 啟動時也會自動同步）。

自己 commit 程式碼時，在訊息裡寫上課題代碼（例如 `SPRINT-W02-S04: 加入 ORE 處理`），App 的任務詳細頁就會列出這些 commit，並連到 GitHub。

## 在其他裝置複習

push 到 GitHub 後，用手機或任何電腦打開 repo 的 `learning/README.md` 或 `learning/QUESTIONS.md` 就能閱讀所有筆記。
