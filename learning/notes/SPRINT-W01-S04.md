# SPRINT-W01-S04：SysTick 與 non-blocking（暫存器）

- 狀態：**進行中**
- 週次：W01　主題：SysTick
- 對應原任務（HAL 版）：W01-S05, W02-S03
- 進行次數：1 次（最近一次：2026-11-03）

## 任務內容

設定 SysTick LOAD/VAL/CTRL 產生 1 ms 中斷，自寫 millis()；重做 non-blocking LED 與按鍵去彈跳狀態機

## 完成標準

tick 計數變數為何要 volatile；32-bit 溢位時 (now - last) 仍正確的原因
