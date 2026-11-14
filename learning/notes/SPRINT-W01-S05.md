# SPRINT-W01-S05：Startup 與 Linker Script

- 狀態：**已完成**
- 階段：基礎　主題：Startup
- 進行次數：2 次（最近一次：2026-11-14）
- 完成日期：2026-11-14
- 複習：0 次，下次 2026-11-15
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

### [筆記] 2026-11-14 19:34

【筆記】向量表前兩項與 BOOT 腳位：上電後硬體先讀兩個 word
**重置後硬體從 0x00000000 載入 SP、從 0x00000004 載入 PC；BOOT 腳位決定 0x00000000 對到哪塊記憶體**

為什麼
- CPU 要執行第一條指令前，必須先知道 stack 在哪（SP）和從哪裡開始執行（PC）
- 這兩個值由硬體自動載入，不靠任何程式碼

上電後硬體做的事
| 順序 | 動作 | 來源位址 | 本專案的值 |
|---|---|---|---|
| 1 | 讀第一個 word → MSP（SP） | `0x00000000` | `0x20005000`（`.word _estack`） |
| 2 | 讀第二個 word → PC，bit 0 → xPSR 的 T bit | `0x00000004` | 向量表存 `0x08000589` → PC = `0x08000588`、`xpsr` = `0x01000000` |
| 3 | 從 PC 開始執行 | — | `Reset_Handler` 的 `ldr r0, =_estack` |

BOOT 腳位（RM0008「儲存器和匯流排架構」→「啟動配置」）
| BOOT1 | BOOT0 | `0x00000000` 對到 | 用途 |
|---|---|---|---|
| x | 0 | 主快閃記憶體（`0x08000000`） | 一般執行自己的程式（本板跳帽） |
| 0 | 1 | 系統記憶體 | ST 出廠 bootloader（UART 燒錄） |
| 1 | 1 | 內建 SRAM | 從 RAM 執行 |

- BOOT0 = 0 時，Flash 同時出現在 `0x00000000` 和 `0x08000000`，兩邊內容完全一樣（Memory 視窗驗證過）
- 啟動檔的 `g_pfnVectors` 被連結到 Flash 最前面，所以向量表第一格就是 `.word _estack`、第二格是 `.word Reset_Handler`

SP 初值為什麼是 `0x20005000`
- SRAM 從 `0x20000000` 開始，20 KB = `0x5000` → 最後一個 byte 在 `0x20004FFF`
- stack 往下長，push 是先減 4 再寫入，所以 SP 初值設在 RAM 結束後的下一個位址，第一次 push 剛好寫進 `0x20004FFC`

PC 為什麼比向量表的值少 1
- Cortex-M3 只能執行 Thumb 指令；ARM 用跳轉位址的 bit 0 = 1 表示「目標是 Thumb 程式碼」
- 向量表存「函式位址 + 1」（奇數），硬體把 bit 0 拆出來放進 xPSR 的 T bit（bit 24），剩下的偶數才放進 PC
- 向量表的值如果 bit 0 = 0 → CPU 想切到 ARM 狀態，但 Cortex-M3 不支援 → HardFault

Debugger 實測（停在 `Reset_Handler` 第一行，`mov sp, r0` 還沒執行）
| 觀察的東西 | 預期 | 實際 | 結論 |
|---|---|---|---|
| `sp` | `0x20005000` | `0x20005000` | 硬體已從向量表載入 |
| `pc` | `Reset_Handler` 的位址（偶數） | `0x08000588` | 和 `.map` 一致 |
| `xpsr` | `0x01000000` | 16777216 = `0x01000000` | 只有 T bit = 1 |
| `0x08000000` 前兩個 word | `0x20005000`、奇數 | `0x20005000`、`0x08000589` | 向量表放在 Flash 開頭 |
| `0x00000000` 前兩個 word | 和 `0x08000000` 相同 | 相同 | BOOT0 = 0 時 Flash 映射到 0 |
| `lr` | — | -1（`0xFFFFFFFF`） | 重置值，沒有可返回的地方 |

其他向量
- 沒實作的中斷都指向 `Default_Handler`（`0x080005D9`），裡面是無窮迴圈
- 自己寫了 `SysTick_Handler` → 覆蓋啟動檔的 `.weak` 版本，`0x0800003C` 那格變成 `0x080002E9`

Debugger 操作：Debug Configurations → Startup 分頁 → Set breakpoint at 改成 `Reset_Handler`，Resume 不勾

### [問題] 2026-11-14 19:35

【問題】把「向量表的 Reset 欄位」和「Reset_Handler 的位址」當成同一件事
**`0x00000004` 是存放位址的格子；格子裡的值（減 1）才是 Reset_Handler 的位址**

- 錯在哪：以為「Reset_Handler 的位址」指的是它在向量表中的位置 `0x00000004`
- 原因：沒分清楚「存放位址的地方」和「被存放的位址」（信封 vs 信封裡寫的地址）
- 正確觀念：
| 名稱 | 是什麼 | 本專案的值 |
|---|---|---|
| 向量表 Reset 欄位 | 固定的格子 | `0x00000004`（= `0x08000004`） |
| 格子裡存的值 | Reset_Handler 位址 + 1 | `0x08000589` |
| Reset_Handler 的位址 | 第一條指令在 Flash 的位置 | `0x08000588`（`.map` 確認） |

### [問題] 2026-11-14 19:35

【問題】以為 SRAM 就是 stack
**SRAM 是整塊 20 KB 的 RAM，stack 只是其中最高處的一段**

- 錯在哪：把 SRAM 和 stack 當成同一個東西
- 正確觀念：SRAM（`0x20000000`～`0x20004FFF`）由低到高依序放 .data → .bss → heap，stack 從最高處 `0x20005000` 往下長
- 各區段的實際範圍，之後讀 `.ld` 和 `.map` 時再確認
