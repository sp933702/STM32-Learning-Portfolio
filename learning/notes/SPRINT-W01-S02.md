# SPRINT-W01-S02：時脈系統（暫存器）

- 狀態：**進行中**
- 週次：W01　主題：RCC
- 對應原任務（HAL 版）：W03-S01
- 進行次數：1 次（最近一次：2026-10-15）

## 任務內容

讀 RM0008 RCC 章節；只用 CMSIS 標頭檔 stm32f1xx.h，手動啟用 HSE、設 Flash latency 2WS、PLL×9 → SYSCLK 72 MHz、APB1 ÷2

## 完成標準

用 debugger 確認 RCC->CFGR 的 SWS 已切到 PLL；能解釋為何先調 Flash latency、APB1 為何最高 36 MHz

## 問題與筆記

### [問題] 2026-10-15 10:51 ❓ 未解決

【卡關】RM0008是甚麼? 我要如何取得?
