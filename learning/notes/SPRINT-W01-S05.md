# SPRINT-W01-S05：Startup 與 Linker Script

- 狀態：**進行中**
- 階段：基礎　主題：Startup
- 進行次數：1 次（最近一次：2026-11-13）
- 程式碼：[projects/SPRINT-W01-S05](../../projects/SPRINT-W01-S05)

## 任務內容

用 debugger 從 Reset_Handler 單步：複製 .data、清 .bss、SystemInit、進 main；讀 .ld 的 MEMORY/SECTIONS；在 .map 找出某全域變數位址與 Flash/RAM 用量

## 完成標準

能 3 分鐘口述「上電到 main」；能指出有初值的全域變數在 Flash 與 RAM 各放哪裡

## 必學範圍

- [ ] 向量表的前兩項（初始 SP、Reset_Handler）與 BOOT 腳位的關係
- [ ] Reset_Handler 做的事：複製 .data、清 .bss、進入 main()
- [ ] .text、.rodata、.data、.bss、heap、stack 各放在 Flash 或 RAM 的哪裡
- [ ] 讀 .ld 的 MEMORY 與 SECTIONS；從 .map 找出變數位址與 Flash／RAM 用量
- [ ] 有初值的全域變數、const、static 區域變數、一般區域變數分別放在哪裡
- [ ] stack overflow 會發生什麼事
- [ ] 3 分鐘口述「上電到 main」

## 問題與筆記

### [筆記] 2026-11-13 14:38

【筆記】SP 與 stack：RAM 裡往下長的暫存區
**SP（R13）存的是位址，指向 stack 目前用到哪裡；Cortex-M3 的 stack 往下長，push 時 SP 先減 4 再寫入**

- stack 是 RAM 裡的一塊區域，放：一般區域變數、函式返回位址、要保留的暫存器、進中斷時硬體自動存的 8 個暫存器
- SP 是 CPU 暫存器 R13，內容是位址，不是資料
- 往下長（full descending）：push 時 `SP = SP - 4`，再寫到 `[SP]`；pop 時讀 `[SP]`，再 `SP = SP + 4`
- stack 用越多 → SP 值越小

| 區域 | 位置 | 成長方向 |
|---|---|---|
| .data、.bss（全域變數） | RAM 低位址 | 固定大小 |
| heap（malloc） | 接在 .bss 後面 | 往上長 |
| stack | RAM 最高處 | 往下長 |

- stack 和 heap 往中間長，撞在一起就是 stack overflow（會蓋掉全域變數或 heap）

### [待學] 2026-11-13 15:07

【待學】exception stack frame（進中斷時硬體自動存的 8 個暫存器）：學 HardFault 除錯時再學
