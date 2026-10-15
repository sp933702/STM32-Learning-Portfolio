# STM32 學習進度

2 個月衝刺：1 / 29 完成（3%）　最後更新：2026-10-15 14:59

- [全部問題整理（複習用）](QUESTIONS.md)

## 2 個月衝刺（暫存器版）

| 代碼 | 任務 | 狀態 | 筆記 |
|---|---|---|---|
| SPRINT-W01-S01 | C 語言驗收 | 已完成 | [5 則](notes/SPRINT-W01-S01.md) |
| SPRINT-W01-S02 | 時脈系統（暫存器） | 進行中 | [6 則](notes/SPRINT-W01-S02.md) |
| SPRINT-W01-S03 | GPIO（暫存器重做） | 未開始 |  |
| SPRINT-W01-S04 | SysTick 與 non-blocking（暫存器） | 未開始 |  |
| SPRINT-W01-S05 | Startup 與 Linker Script | 未開始 |  |
| SPRINT-W02-S01 | EXTI + NVIC（暫存器） | 未開始 |  |
| SPRINT-W02-S02 | Timer 週期中斷（暫存器） | 未開始 |  |
| SPRINT-W02-S03 | PWM（暫存器） | 未開始 |  |
| SPRINT-W02-S04 | USART 暫存器驅動 | 未開始 |  |
| SPRINT-W02-S05 | CLI 移植到暫存器驅動 | 未開始 |  |
| SPRINT-W03-S01 | DMA（暫存器） | 未開始 |  |
| SPRINT-W03-S02 | Driver / BSP / App 分層 | 未開始 |  |
| SPRINT-W03-S03 | 統一錯誤碼與 timeout | 未開始 |  |
| SPRINT-W04-S01 | I²C 協定與軟體 I²C | 未開始 |  |
| SPRINT-W04-S02 | 陀螺儀驅動（照 datasheet） | 未開始 |  |
| SPRINT-W04-S03 | 硬體 I²C（暫存器） | 未開始 |  |
| SPRINT-W05-S01 | SPI 暫存器驅動 | 未開始 |  |
| SPRINT-W05-S02 | SPI Flash 驅動 | 未開始 |  |
| SPRINT-W05-S03 | SPI 螢幕驅動 + 共用匯流排 | 未開始 |  |
| SPRINT-W06-S01 | IWDG + Reset 原因 | 未開始 |  |
| SPRINT-W06-S02 | HardFault 除錯 | 未開始 |  |
| SPRINT-W06-S03 | 姿態記錄器整合 | 未開始 |  |
| SPRINT-W06-S04 | 履歷初稿與開始投遞 | 未開始 |  |
| SPRINT-W07-S01 | Python 串口工具與自動化測試 | 未開始 |  |
| SPRINT-W07-S02 | GitHub 作品整理 | 未開始 |  |
| SPRINT-W07-S03 | 補觀念：RTOS 與 Register Map | 未開始 |  |
| SPRINT-W08-S01 | C 與嵌入式題庫 | 未開始 |  |
| SPRINT-W08-S02 | 專案介紹與追問演練 | 未開始 |  |
| SPRINT-W08-S03 | 模擬面試與持續投遞 | 未開始 |  |

## 原計畫（HAL 版）

| 代碼 | 任務 | 狀態 | 筆記 |
|---|---|---|---|
| STM32-W00-S01 | 確認晶片與板型 | 已完成 | [筆記](notes/STM32-W00-S01.md) |
| STM32-W00-S02 | 安裝開發工具 | 已完成 | [筆記](notes/STM32-W00-S02.md) |
| STM32-W00-S03 | 閱讀四類文件 | 已完成 | [筆記](notes/STM32-W00-S03.md) |
| STM32-W01-S01 | 建立第一個專案 | 已完成 | [筆記](notes/STM32-W01-S01.md) |
| STM32-W01-S02 | 第一次燒錄 | 已完成 | [筆記](notes/STM32-W01-S02.md) |
| STM32-W01-S03 | HAL LED Blink | 已完成 | [筆記](notes/STM32-W01-S03.md) |
| STM32-W01-S04 | Debugger 基礎 | 已完成 | [筆記](notes/STM32-W01-S04.md) |
| STM32-W01-S05 | Non-blocking LED | 已完成 | [筆記](notes/STM32-W01-S05.md) |
| STM32-W02-S01 | 按鍵輪詢 | 已完成 | [筆記](notes/STM32-W02-S01.md) |
| STM32-W02-S02 | 外部中斷 | 已完成 | [筆記](notes/STM32-W02-S02.md) |
| STM32-W02-S03 | 按鍵除彈跳 | 已完成 |  |
| STM32-W03-S01 | 硬體計時器 | 已完成 | [筆記](notes/STM32-W03-S01.md) |
| STM32-W03-S02 | PWM 輸出 | 已完成 | [筆記](notes/STM32-W03-S02.md) |
| STM32-W04-S01 | UART Polling 傳送 | 已完成 | [筆記](notes/STM32-W04-S01.md) |
| STM32-W04-S02 | UART Polling 接收 | 已完成 | [筆記](notes/STM32-W04-S02.md) |
| STM32-W05-S01 | Interrupt RX | 已完成 | [筆記](notes/STM32-W05-S01.md) |
| STM32-W05-S02 | Ring Buffer | 已完成 | [筆記](notes/STM32-W05-S02.md) |
| STM32-W05-S03 | 命令解析器 | 已完成 | [筆記](notes/STM32-W05-S03.md) |
| STM32-W06-S01 | 單次 ADC | 已完成 | [筆記](notes/STM32-W06-S01.md) |
| STM32-W06-S02 | 週期取樣與濾波 | 已完成 | [筆記](notes/STM32-W06-S02.md) |
| STM32-W07-S01 | ADC DMA | 已完成 | [筆記](notes/STM32-W07-S01.md) |
| STM32-W07-S02 | UART DMA | 已完成 | [筆記](notes/STM32-W07-S02.md) |
| STM32-W08-S01 | I²C Master | 進行中 | [筆記](notes/STM32-W08-S01.md) |
| STM32-W08-S02 | SPI Master | 暫緩 | [筆記](notes/STM32-W08-S02.md) |
| STM32-W09-S01 | Driver / BSP / App 分層 | 進行中 |  |
| STM32-W09-S02 | 統一錯誤碼 | 暫緩 | [筆記](notes/STM32-W09-S02.md) |
| STM32-W10-S01 | Watchdog | 未開始 |  |
| STM32-W10-S02 | Reset Reason | 未開始 |  |
| STM32-W10-S03 | HardFault 除錯 | 未開始 |  |
| STM32-W11-S01 | Task 與排程 | 未開始 |  |
| STM32-W11-S02 | Queue / Semaphore | 未開始 |  |
| STM32-W11-S03 | 共享資源與死鎖 | 未開始 |  |
| STM32-W12-S01 | Python 串口測試 | 未開始 |  |
| STM32-W12-S02 | 邊界與錯誤測試 | 未開始 |  |
| STM32-W13-S01 | STM32 Driver Lab | 未開始 |  |
| STM32-W14-S01 | 模擬 IC Register Map | 未開始 |  |
| STM32-W15-S01 | 自動化 IC 驗證 | 未開始 |  |
| STM32-W16-S01 | 作品集整理 | 未開始 |  |
| STM32-W16-S02 | 面試題整理 | 未開始 |  |
