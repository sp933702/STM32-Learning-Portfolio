# SPRINT-W02-S01：EXTI + NVIC（暫存器）

- 狀態：**進行中**
- 階段：中斷與通訊　主題：EXTI
- 進行次數：1 次（最近一次：2026-11-24）
- 程式碼：[projects/SPRINT-W02-S01](../../projects/SPRINT-W02-S01)

## 任務內容

AFIO_EXTICR 選 PB0，設定 EXTI IMR/FTSR，NVIC 設優先權並致能；ISR 中清除 PR 旗標

## 完成標準

故意不清 PR 觀察現象並解釋；能說明搶佔優先權與子優先權；ISR 該做與不該做的事

## 必學範圍

- [ ] AFIO_EXTICR 選腳位；EXTI 的 IMR、RTSR、FTSR
- [ ] PR 寫 1 清除，以及為什麼不能用讀改寫
- [ ] NVIC：致能、優先權分組、搶佔優先權與子優先權
- [ ] 向量表和 handler 名稱的對應
- [ ] ISR 該做與不該做的事
- [ ] ISR 與主迴圈共享變數：volatile、臨界區（暫時關中斷）、非原子操作造成的競爭
- [ ] 中斷延遲與巢狀中斷的概念
- [ ] 按鍵用 EXTI 和用輪詢去彈跳的比較
