# SPRINT-W01-S05：Startup 與 Linker Script

- 狀態：**進行中**
- 階段：基礎　主題：Startup
- 進行次數：1 次（最近一次：2026-11-13）

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
