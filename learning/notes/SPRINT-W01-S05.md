# SPRINT-W01-S05：Startup 與 Linker Script

- 狀態：**進行中**
- 階段：基礎　主題：Startup
- 進行次數：3 次（最近一次：2026-11-14）
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

### [筆記] 2026-11-14 20:33

【筆記】Cortex-M3 暫存器與常見縮寫的全名
**SP = Stack Pointer（R13）、LR = Link Register（R14）、PC = Program Counter（R15）**

| 縮寫 | 全名 | 中文 | 用途 |
|---|---|---|---|
| R0–R12 | General-purpose registers | 通用暫存器 | 計算、傳參數（R0–R3 傳函式參數和回傳值） |
| SP（R13） | Stack Pointer | 堆疊指標 | 指向 stack 目前用到的位址 |
| MSP | Main Stack Pointer | 主堆疊指標 | 重置後使用的 SP，從向量表第一格載入 |
| PSP | Process Stack Pointer | 行程堆疊指標 | 給 RTOS 的工作用，裸機程式不用 |
| LR（R14） | Link Register | 連結暫存器 | 存函式的返回位址；重置值 `0xFFFFFFFF` |
| PC（R15） | Program Counter | 程式計數器 | 下一條要執行的指令位址 |
| xPSR | Program Status Register | 程式狀態暫存器 | 運算旗標、T bit（bit 24）、目前的例外編號 |
| T bit | Thumb state bit | Thumb 狀態位元 | 1 = Thumb 狀態；Cortex-M3 必須一直是 1 |
| SRAM | Static Random Access Memory | 靜態隨機存取記憶體 | 晶片內的 RAM，斷電就消失 |
| ISR | Interrupt Service Routine | 中斷服務函式 | 向量表每一格指向的函式 |

- 一定要記的：SP、LR、PC 三個的全名和編號，面試常問
- 查文件：PM0056「The Cortex-M3 processor」→「Core registers」

### [筆記] 2026-11-14 20:35

【筆記】連結器會丟掉沒人引用的函式與變數：--gc-sections 與 KEEP
**CubeIDE 預設讓每個函式和變數各占一個區段，連結時沒有人引用的區段整個丟掉，-O0 也一樣**

| | 編譯器最佳化（-O2） | 連結器 gc-sections |
|---|---|---|
| 誰做的 | 編譯器（`.c` → `.o`） | 連結器（`.o` → `.elf`） |
| 刪什麼 | 函式內多餘的讀寫、迴圈 | 整個沒人引用的函式或變數 |
| 開關 | `-O0` / `-O2` | `-ffunction-sections -fdata-sections` + `--gc-sections` |

- 只宣告、沒用到的全域變數 → 從 `.map` 消失 → 測試時要在程式裡讀它一次
- 向量表沒有程式用名字引用（是硬體去讀的）→ `.ld` 要寫 `KEEP(*(.isr_vector))`，否則會被丟掉
- CubeIDE 查看位置：專案 Properties → C/C++ Build → Settings → MCU GCC Compiler → Optimization；MCU GCC Linker → General
- 和 -O2 的關係：兩者疊加；-O2 刪函式內的程式碼，gc-sections 刪整個沒用到的東西

### [筆記] 2026-11-14 20:39

【筆記】Reset_Handler 用到的組合語言指令
**ldr 讀、str 寫、mov 複製、b／bl 跳、cmp＋bcc 比較後條件跳躍**

| 指令 | 全名 | 意思 | 啟動檔裡的例子 |
|---|---|---|---|
| `ldr r0, =符號` | Load Register | 把符號的**值**（位址）放進 r0 | `ldr r0, =_estack` → r0 = `0x20005000` |
| `ldr r4, [r2, r3]` | Load Register | 到記憶體位址 `r2 + r3` **讀**一個 word 放進 r4 | 從 Flash 讀初值 |
| `str r4, [r0, r3]` | Store Register | 把 r4 **寫**到記憶體位址 `r0 + r3` | 寫進 RAM |
| `mov sp, r0` | Move | 把 r0 複製到 sp | 設定堆疊指標 |
| `movs r3, #0` | Move（s = 更新旗標） | r3 = 0 | 計數器歸零 |
| `adds r3, r3, #4` | Add | r3 = r3 + 4 | 往下一個 word |
| `cmp r4, r1` | Compare | 比較 r4 和 r1，結果記在旗標 | 檢查是否搬到結尾 |
| `bcc 標籤` | Branch if Carry Clear | 上一次 cmp 結果是「小於」（無號數）就跳 | 還沒到結尾就繼續 |
| `b 標籤` | Branch | 無條件跳躍 | `b LoopForever` |
| `bl 函式` | Branch with Link | 跳到函式，並把返回位址存進 LR | `bl main` |

- `#` 開頭是常數；`[ ]` 代表「到這個位址去讀寫記憶體」
- `ldr r0, =_estack` 在反組譯（`.list`）裡會變成 `ldr r0, [pc, #52]`：組譯器把常數存在程式碼附近，再用 PC 相對位址讀出來
- 查文件：PM0056「The Cortex-M3 instruction set」

### [筆記] 2026-11-14 20:55

【筆記】本專案的 SystemInit 被換成 nop：weak 符號沒有定義
**啟動檔宣告 `.weak SystemInit` 但專案沒有 system_stm32f1xx.c，連結器把 `bl SystemInit` 換成 `nop.w`，什麼都沒做**

| 檔案 | 看到什麼 |
|---|---|
| `startup_stm32f103c8tx.s` 第 61 行 | `bl  SystemInit` |
| `startup_stm32f103c8tx.s` 第 423 行 | `.weak	SystemInit`（只宣告，沒有定義） |
| `.map` | 搜尋不到 `SystemInit` |
| `.list` 的 `<Reset_Handler>:` | `800059c: f3af 8000  nop.w` |

- 一般符號沒定義 → 連結錯誤 `undefined reference`
- weak 符號沒定義 → 不報錯，值當作 0；`bl` 到它的指令被換成 `nop`
- weak 有人定義 → 用那個定義（例如自己寫的 `SysTick_Handler` 覆蓋 `Default_Handler`）
- `SystemInit` 是 CMSIS 規定的名稱，用來放「進 main 前的晶片初始化」；用 HAL／CubeMX 的專案會由 `system_stm32f1xx.c` 提供
- 本專案的時脈設定由 `main()` 裡的 `Clock_Init()` 負責，所以 `SystemInit` 沒做事也正常
- 除錯應用：懷疑某個函式「根本沒被呼叫」時，到 `.list` 看呼叫處實際編出了什麼指令

### [問題] 2026-11-14 20:57

【問題】以為未初始化的 RAM 會是某個有意義的值
**剛上電時 SRAM 內容不確定；debugger 重新執行時沒斷電，RAM 還留著上一次的值**

- 錯在哪：猜複製 .data 前 `g_test_data` 會是 `0x080005D9`（Default_Handler 位址 + 1）
- 原因：把 Flash 裡的向量表和 RAM 混在一起
- 正確觀念：SRAM 上電後是亂碼，要靠 Reset_Handler 複製 .data、清 .bss 才有正確初值
- 實驗陷阱：debugger 重新開始 ≠ 斷電，RAM 會保留上次的值；觀察前先在 Memory 視窗手動填入 `DEADBEEF`

### [筆記] 2026-11-14 20:59

【筆記】STM32F103 的記憶體種類與記憶體映像
**Flash 斷電保留、放程式與初值；SRAM 斷電消失、放變數與 stack；周邊暫存器也有位址，用讀寫記憶體的方式操作**

| 種類 | 位址（記憶體映像） | 斷電後 | 寫入方式 | 放什麼 |
|---|---|---|---|---|
| 主 Flash（64 KB） | `0x08000000`～`0x0800FFFF` | 保留 | 要先整頁擦除再寫，慢 | 向量表、程式碼（.text）、常數（.rodata）、.data 的**初值** |
| 系統記憶體 | `0x1FFFF000` 起 | 保留（出廠燒好） | 不能改 | ST 的 bootloader（BOOT0 = 1 時執行） |
| SRAM（20 KB） | `0x20000000`～`0x20004FFF` | **消失** | 隨時讀寫，快 | .data、.bss、heap、stack |
| 周邊暫存器 | `0x40000000` 起 | — | 讀寫位址就是操作硬體 | `RCC`、`GPIOC`、`FLASH->ACR`…… |
| Cortex-M3 核心周邊 | `0xE0000000` 起 | — | 同上 | SysTick、NVIC |

- 有初值的全域變數有兩份：初值存在 Flash（斷電要保留），執行時的變數在 SRAM（要能改）→ 啟動時由 Reset_Handler 從 Flash 複製到 SRAM
- 查文件：RM0008「儲存器和匯流排架構」→「儲存器映像」；容量看《STM32F103x8 Datasheet》
