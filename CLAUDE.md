# STM32 → IC 韌體工程師轉職：給 Claude 的背景說明

> 這份檔案讓任何一台電腦上的 Claude（Claude Code 或 claude.ai）都能接續同一個學習進度。
> 每完成一項任務，請更新「目前進度」一節，並與進度表同步。

## 學習者
- 電機系畢業，會基礎 C 與 Python，嵌入式自學中。
- 目標：台灣 IC 設計公司軟韌體工程師（例如奇景光電、義隆電子、新唐、光寶科），偏好南部。
- 回覆請使用**繁體中文**。

## 硬體與環境
- MCU：STM32F103C8T6（Blue Pill 相容板，USB Type-C，無板載 ST-LINK）
- 燒錄／除錯：外接 ST-LINK V2，SWD
- 板載 LED：PC13，Active-Low；按鍵：PB0，Input Pull-up
- 周邊模組：USB 轉 TTL、邏輯分析儀（24 MHz 8CH）、I²C 陀螺儀（推測 MPU6050）、SPI 螢幕（推測 SSD1306 OLED）、SPI Flash（推測 W25Q64）
- 軟體：STM32CubeIDE 2.2.0、STM32CubeMX 6.18、STM32CubeProgrammer
- 兩台 Windows 電腦，以 Git 同步專案（不同步 `.metadata`、`Debug/`）

## 已完成（HAL 版）
- STM32-W00～W07：環境、燒錄、GPIO、Debugger、Non-blocking、按鍵輪詢、EXTI、Debounce、TIM 中斷、PWM、UART Polling／Interrupt、Ring Buffer、命令解析器（CLI）、ADC、ADC DMA、UART DMA
- 進行中（舊表）：W08-S01 I²C、W09-S01 分層架構
- 樹莓派純軟體模擬 Day1–4：位元運算、struct／pointer／volatile、GPIO 驅動分層、Blocking／Non-blocking 狀態機

## 目前計畫：2 個月衝刺（2026-10-15 ～ 2026-12-09）
- 課題代碼格式 `SPRINT-Wxx-Sxx`（原 HAL 版為 `STM32-Wxx-Sxx`）；進度已從 Excel 改由學習進度 App 管理
- 原則：**全部改用暫存器重做**（只用 CMSIS 標頭檔 `stm32f1xx.h`，不使用 HAL），每項對照 RM0008 章節，並與舊 HAL 版比較

| 週 | 內容 |
|---|---|
| W01 | C 驗收、RCC 72 MHz、GPIO、SysTick、Startup／Linker Script |
| W02 | EXTI＋NVIC、Timer、PWM、USART、CLI 移植 |
| W03 | DMA、Driver／BSP／App 分層、統一錯誤碼與 timeout |
| W04 | 軟體 I²C → 陀螺儀驅動 → 硬體 I²C（同一驅動換底層） |
| W05 | SPI 驅動、SPI Flash、SPI 螢幕（共用匯流排、各自 CS、DMA） |
| W06 | IWDG＋Reset 原因、HardFault 除錯、專案整合、開始投履歷 |
| W07 | Python 自動化測試、GitHub 作品整理、RTOS 與 Register Map 觀念 |
| W08 | 面試題庫、專案介紹演練、模擬面試 |

- 作品集專案：**姿態感測資料記錄器**（I²C 陀螺儀＋SPI 螢幕＋SPI Flash 共用 SPI、UART CLI、Python 電腦端工具）

## 目前進度
- **以 `learning/progress.json` 為準**（狀態、問題與筆記都在這裡；`learning/README.md` 是可讀版總覽）。
- 開始協助前，先讀 progress.json 找出狀態為「進行中」的課題與它的筆記；沒有的話就接續第一個「未開始」的 SPRINT 課題。
- 各課題程式碼在 `projects/<課題代碼>/`。

## 這個 repo 的工具
- 學習進度 App：`tracker/app.py`（雙擊根目錄的 `STM32Tracker.exe`，以 pythonw 背景執行；所有分頁關閉後自動結束）。學習者用它開始／結束課題、記錄問題與筆記、上傳程式碼；結束課題時會自動 commit、打 tag、push。
- 學習者開始課題時會貼上 App 產生的「開始提示詞」，卡關時貼上「求助提示詞」，請依提示詞裡的步驟引導。
- 請不要手動改寫 `learning/README.md`、`learning/QUESTIONS.md`、`learning/notes/`，它們由 App 自動產生。
- 協助寫 commit 訊息時，在開頭加上課題代碼（例如 `SPRINT-W02-S04: ...`），App 會據此把 commit 連到課題。

## 教學方式
- 引導式教學：先說明本任務目標與檢查方式，**不要一次給完整答案**。
- 暫存器任務：先請學習者找出 RM0008 對應章節與暫存器，再寫程式，最後與 HAL 版比較。
- 驗收依進度表的「完成標準」，不只看程式能不能動。

## 參考文件（「STM32 練習/参考文档」）
- RM0008 參考手冊、PM0056 Cortex-M3 程式設計手冊、STM32F103x8 Datasheet、Flash 程式設計手冊、Cortex-M3 權威指南
