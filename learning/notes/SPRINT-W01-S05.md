# SPRINT-W01-S05：Startup 與 Linker Script

- 狀態：**進行中**
- 階段：基礎　主題：Startup
- 進行次數：9 次（最近一次：2026-11-24）
- 程式碼：[projects/SPRINT-W01-S05](../../projects/SPRINT-W01-S05)

## 任務內容

用 debugger 從 Reset_Handler 單步：複製 .data、清 .bss、SystemInit、進 main；讀 .ld 的 MEMORY/SECTIONS；在 .map 找出某全域變數位址與 Flash/RAM 用量

## 完成標準

能 3 分鐘口述「上電到 main」；能指出有初值的全域變數在 Flash 與 RAM 各放哪裡

## 必學範圍

- [x] 向量表的前兩項（初始 SP、Reset_Handler）與 BOOT 腳位的關係
- [x] Reset_Handler 做的事：複製 .data、清 .bss、進入 main()
- [x] .text、.rodata、.data、.bss、heap、stack 各放在 Flash 或 RAM 的哪裡
- [x] 讀 .ld 的 MEMORY 與 SECTIONS；從 .map 找出變數位址與 Flash／RAM 用量
- [x] 有初值的全域變數、const、static 區域變數、一般區域變數分別放在哪裡
- [x] stack overflow 會發生什麼事
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

### [筆記] 2026-11-15 22:36

【筆記】little-endian：最低位的 byte 放在最低的位址
**`0x12345678` 在記憶體裡依位址由低到高存成 `78 56 34 12`；Cortex-M3 是 little-endian**

| 位址 | +0 | +1 | +2 | +3 |
|---|---|---|---|---|
| 內容 | `78` | `56` | `34` | `12` |

- Memory 視窗用 Hex（逐 byte）顯示 → 看到 `78563412`；改用 Hex Integer → 看到 `12345678`
- 看 Memory 視窗前先確認顯示格式，否則會以為資料被寫錯
- 之後用 UART／SPI 傳多 byte 資料、或用邏輯分析儀看波形時，也要注意 byte 順序

### [筆記] 2026-11-15 22:58

【筆記】有初值的全域變數有兩個位址：Flash 存初值、RAM 放變數
**連結器在 Flash 和 RAM 用同樣順序排 .data，所以初值位址 = `_sidata` +（變數位址 − `_sdata`）**

| | 名稱 | 本專案 | 用途 |
|---|---|---|---|
| Flash 那份 | LMA（Load Memory Address，載入位址） | `_sidata` = `0x08000654` | 存初值，斷電保留 |
| RAM 那份 | VMA（Virtual Memory Address，執行位址） | `_sdata` = `0x20000000` | 程式讀寫的變數 |

- 公式：`初值在 Flash 的位址 = _sidata + (變數位址 − _sdata)`
- 這個公式就是複製迴圈：`ldr r4, [r2, r3]`（Flash）→ `str r4, [r0, r3]`（RAM），r3 是偏移量，每次 +4
- 實測：`g_test_data` 在 `0x20000000`，偏移量 0 → 初值在 `0x08000654`，Memory 視窗看到 `12345678`
- 本專案 .data 只有 4 byte（只有 `g_test_data`），迴圈跑 1 圈；.bss 有 `0x30` = 48 byte，清 12 個 word

### [問題] 2026-11-15 22:59

【問題】SystemInit 執行時，全域變數還不能用
**SystemInit 排在複製 .data、清 .bss 之前，這時所有全域變數和 static 變數都是亂碼**

- 實測：停在 `bl SystemInit`（啟動檔第 61 行）時，`g_test_data` = `DEADBEEF`，不是 `0x12345678`
- 不能用：有初值的全域變數（.data 還沒複製）、沒初值的全域變數（.bss 還沒清 0，「預設為 0」還不成立）、static 區域變數
- 可以用：一般區域變數（在 stack 上，SP 在第 59 行已經設好）、直接讀寫暫存器
- 為什麼排在前面：外接 SRAM 要先初始化記憶體控制器才能放 .data；先調快時脈讓複製迴圈變快
- 面試版：「SystemInit 在 C 執行環境準備好之前執行，只能操作暫存器，不能依賴全域變數的初值」

### [解法] 2026-11-15 23:00

【解法】從 Reset_Handler 單步到 main：設 SP → SystemInit → 複製 .data → 清 .bss → main
**Reset_Handler 先設好 SP，再把 .data 初值從 Flash 搬到 RAM、把 .bss 清 0，C 語言對全域變數的保證才成立，最後才能進 main**

整體流程
`硬體載入 SP、PC → 設 SP → SystemInit（本專案為 nop）→ 複製 .data → 清 .bss → __libc_init_array → main`

| 步驟 | 啟動檔 | 做了什麼 | 為什麼 |
|---|---|---|---|
| 設 SP | 第 58–59 行 `ldr r0, =_estack`、`mov sp, r0` | SP = `0x20005000` | 從 bootloader 跳進來、或 debugger 直接設 PC 時，硬體不會讀向量表，SP 可能是別人的值 → 保險再設一次 |
| SystemInit | 第 61 行 `bl SystemInit` | 本專案被換成 `nop.w`（weak 沒有定義） | 晶片初始化（時脈、外接記憶體）；這時全域變數還不能用 |
| 複製 .data | 第 64–78 行 | 從 `_sidata`（Flash）複製到 `_sdata`～`_edata`（RAM） | 有初值的全域變數，初值存在 Flash，要搬到 RAM 才能讀寫 |
| 清 .bss | 第 81–92 行 | `_sbss`～`_ebss` 寫 0 | C 語言保證沒初值的全域變數是 0，靠這裡做到 |
| `__libc_init_array` | 第 96 行 | 呼叫 C 函式庫的初始化（C++ 建構子等） | 要用到全域變數，排在 .data／.bss 之後 |
| main | 第 99 行 `bl main` | 進入使用者程式 | 前面全部準備好，C 環境才完整 |
| main 回來 | 第 101–102 行 `LoopForever` | 無窮迴圈 | 裸機的 main 不該返回，返回了也不會亂跑 |

複製迴圈怎麼運作
- r0 = `_sdata`、r1 = `_edata`、r2 = `_sidata`、r3 = 偏移量（從 0 開始）
- `ldr r4, [r2, r3]` 從 Flash 讀 → `str r4, [r0, r3]` 寫到 RAM → `adds r3, r3, #4`
- `cmp` + `bcc`：`_sdata + r3` 還小於 `_edata` 就繼續

觀察紀錄（停在 Reset_Handler 時先把兩個變數手動填成 `DEADBEEF`，模擬上電亂碼）
| 觀察的東西 | 預期 | 實際 | 結論 |
|---|---|---|---|
| `bl SystemInit` 的機器碼（`.list`） | 跳到 SystemInit | `nop.w` | weak 沒定義 → 連結器換成 nop |
| r0／r1／r2 | `_sdata`／`_edata`／`_sidata` | `0x20000000`／`0x20000004`／`0x08000654` | 和 `.map` 一致 |
| `g_test_data`（第 81 行前） | `0x12345678` | `78563412`（逐 byte 顯示） | 已從 Flash 複製；little-endian |
| `g_test_bss`（第 81 行前） | 還是 `DEADBEEF` | `DEADBEEF` | .bss 還沒清 |
| `g_test_bss`（第 96 行前） | 0 | `00000000` | .bss 已清 0 |
| Flash `0x08000654` | `12345678` | `12345678` | 初值存在 Flash 的 `_sidata` |
| 最後 | 進 main | 停在 `(void)g_test_data;` | 流程完成 |

位址（`.map`）
| 符號 | 位址 | 說明 |
|---|---|---|
| `_sidata` | `0x08000654` | .data 初值在 Flash 的起點 |
| `_sdata`／`_edata` | `0x20000000`／`0x20000004` | .data 只有 4 byte（只有 `g_test_data`） |
| `_sbss`／`_ebss` | `0x20000004`／`0x20000034` | .bss 共 48 byte，`g_test_bss` 在 `0x20000030` |

為什麼是這個順序
- SP 一定第一個：SystemInit 是 C 函式，會用到 stack
- SystemInit 在複製之前：可能要先初始化放 .data 的記憶體
- .data、.bss 在 main 之前：main 一開始就可能讀全域變數
- .data 和 .bss 兩者互不依賴，誰先都可以

Debugger 操作
- Debug Configurations → Startup → Set breakpoint at `Reset_Handler`
- Memory 視窗點兩下值可以直接改（用來填 `DEADBEEF`）
- 迴圈不要一直按 F5：在迴圈後一行設中斷點，按 F8（Resume）
- F5 = Step Into（進入函式）、F6 = Step Over（跨過函式）

### [筆記] 2026-11-15 23:15

【筆記】區域變數的初值寫在指令裡，只要 SP 正確就能用
**全域變數的初值存在 Flash 資料區、上電時複製一次；區域變數的初值是函式指令的一部分，每次呼叫時才寫進 stack**

`Clock_Init()` 的反組譯（`.list`）
```
push  {r7}           ; SP -4，保存 r7
sub   sp, #12        ; SP -12，在 stack 上挖出區域變數的空間
add   r7, sp, #0     ; r7 = SP，當作找區域變數的基準
movs  r3, #0         ; count 的初值 0 寫在指令裡
str   r3, [r7, #4]   ; 寫進 stack
```

| | 全域變數 | 區域變數 |
|---|---|---|
| 初值存在哪 | Flash .data 初值區（`_sidata` 起） | 函式指令裡 |
| 何時放進 RAM | 上電時 Reset_Handler 複製一次 | 每次呼叫函式時 |
| 前提 | 複製 .data 完成 | SP 正確 |

- 所以 SystemInit 裡可以用區域變數，不能依賴全域變數
- 啟動檔只需要 `_estack`（stack 頂端），stack 的底沒有符號、CPU 也不檢查 → stack overflow 不會被發現

### [筆記] 2026-11-16 22:03

【筆記】.ld 的 MEMORY 與 SECTIONS：連結器用位置計數器 . 依序排放
**MEMORY 定義有哪些記憶體，SECTIONS 依序把各區段排進去；`.` 是目前排到的位置，`_sdata` 這些符號都是記下 `.` 的結果**

MEMORY
| 名稱 | 屬性 | 起點 | 大小 | 意義 |
|---|---|---|---|---|
| FLASH | `rx` | `0x08000000` | 64K | 可讀、可執行；不能用 `str` 寫 |
| RAM | `xrw` | `0x20000000` | 20K | 可讀寫，也能執行（`.RamFunc`） |

- `r` = read、`w` = write、`x` = execute（可執行程式碼），不是 r+w
- 大小來自《STM32F103x8 Datasheet》，CubeIDE 依型號產生

SECTIONS（依排放順序）
| 區段 | 放到 | 內容 |
|---|---|---|
| `.isr_vector` | `>FLASH` | 向量表，`KEEP` 防止被丟掉 |
| `.text` | `>FLASH` | 程式碼 |
| `.rodata` | `>FLASH` | 常數、字串 |
| `.data` | `>RAM AT> FLASH` | 有初值的全域變數：執行位址在 RAM，初值放在 Flash |
| `.bss` | `>RAM` | 沒初值的全域變數 |
| `._user_heap_stack` | `>RAM` | 不放東西，只推游標檢查空間 |

- `>RAM` = 執行位址（VMA）；`AT> FLASH` = 載入位址（LMA）
- `_sidata = LOADADDR(.data);` = 取 .data 的載入位址 → `0x08000654`
- `_estack = ORIGIN(RAM) + LENGTH(RAM);` → `0x20005000`

位置計數器 `.`（location counter）
- 代表「目前排到的位址」，每放一樣東西就往後移
- `_sdata = .;` 寫在 `*(.data)` 之前、`_edata = .;` 寫在之後 → 兩個值不同
- 位址不是寫死的，程式一改，後面的位址全部會移動
- `. = ALIGN(4);` = 對齊到 4 的倍數；`. = . + N;` = 往後空出 N byte

`._user_heap_stack`（本專案實測）
| 動作 | `.` 的值 |
|---|---|
| `.bss` 結束 | `0x20000034` |
| `ALIGN(8)`，`_end = .`（heap 起點） | `0x20000038` |
| `+ _Min_Heap_Size`（`0x200`） | `0x20000238` |
| `+ _Min_Stack_Size`（`0x400`） | `0x20000638` |

- 用途：檢查 .data + .bss 之後還留得下 heap 512 byte + stack 1 KB，超過 RAM 就連結失敗 `region 'RAM' overflowed`
- 不是 stack 的實際位置：stack 在 RAM 頂端 `0x20005000` 往下長
- `sysmem.c` 的 `_sbrk()`：heap 從 `&_end` 開始，上限 `_estack − _Min_Stack_Size`，超過時 `malloc` 回傳 `NULL`
- 保護不到：執行時 stack 實際用超過 1 KB → 往下長進空閒空間，撞到 heap／.bss 也沒人檢查

RAM 配置（低 → 高）
`.data → .bss → heap（往上）→ 空閒 → stack（往下）`

### [問題] 2026-11-18 22:21

【問題】把 0x2000xxxx 的位址判斷成 Flash
**位址開頭決定記憶體種類：0x0800 是 Flash、0x2000 是 RAM**

- 錯在哪：`s_test_count`（`0x20000004`）、`s_test_zero`、`g_test_sink` 都寫成 Flash
- 正確判斷：
| 位址開頭 | 記憶體 |
|---|---|
| `0x0800xxxx` | Flash（程式、常數、.data 初值） |
| `0x2000xxxx` | SRAM（.data、.bss、heap、stack） |
| `0x4000xxxx` | 周邊暫存器 |
| `0xE000xxxx` | Cortex-M3 核心周邊（SysTick、NVIC） |
- 除錯應用：指標值是 `0x0800xxxx` → 指向 Flash，寫入一定失敗

### [問題] 2026-11-18 22:21

【問題】以為 static 區域變數放在 stack
**static 讓變數壽命和程式一樣長，所以放在 .data／.bss，不在 stack；只有能見範圍限制在函式內**

- 錯在哪：預測 `s_test_count`、`s_test_zero` 在 stack
- 實際：`s_test_count`（有初值）→ `.data.s_test_count.1`，`0x20000004`；`s_test_zero`（沒初值）→ `.bss.s_test_zero.0`，`0x2000003C`
- 原因：stack 上的東西函式結束就回收，static 要保留到下次呼叫，只能放 .data／.bss
- `.map` 名字後的 `.0`、`.1` 是編譯器加的編號，避免不同函式的同名 static 變數撞名
- 面試版：「static 區域變數和全域變數放在同一個地方，差別只在誰看得到它的名字」

### [問題] 2026-11-18 22:22

【問題】把 .map 的 Discarded input sections 裡的 0x00000000 當成實際位址
**`.map` 開頭的 Discarded input sections 列的是被丟掉的區段，位址一律顯示 0，不是真的位址**

- 錯在哪：看到 `.rodata.g_test_const 0x00000000`，以為 `g_test_const` 放在 `0x00000000`
- 實際：那一行在 `.map` 的 `Discarded input sections` 段落裡（第 42 行起）→ 被連結器丟掉了；debugger 看 `&g_test_const` 也顯示 Error
- 被丟的原因：`const` 的值在編譯時已知，編譯器直接把 `0xCAFEBABE` 寫進程式碼（`.list` 的 `.word 0xcafebabe`），沒人引用變數本身 → `--gc-sections` 丟掉
- 查 `.map` 時，先確認那一行在哪個段落底下，再看位址

### [問題] 2026-11-18 22:42

【問題】以為有初值、有人用的 const 全域變數會放在 .data
**const 全域變數放在 .rodata，只在 Flash，不會複製到 RAM**

- 錯在哪：預測 `const volatile uint32_t g_test_const = 0xCAFEBABEU;` 會在 `.data`、位址 `0x2000xxxx`
- 實際：`.rodata`、`0x080006A4`；`text` +4，`data` 不變（沒有被複製）
- 原因：值不會變，不需要可寫的 RAM 副本，直接從 Flash 讀
- 應用：大的查表陣列（字型、正弦表）加 `const` → 留在 Flash，不佔 RAM
- 補充：沒加 `volatile` 時，編譯器把值直接寫進指令，變數本身被 `--gc-sections` 丟掉

### [問題] 2026-11-18 22:43

【問題】以為 debugger 改不了 const 變數是因為 C 的 const
**改不了是因為位址在 Flash（不能用一般寫入），不是因為 const 關鍵字**

- 現象：Memory 視窗改 `0x080006A4` → `Edit failed: Error writing memory block`
- 原因：debugger 不認得 C 關鍵字，只是對位址寫入；Flash 要透過 Flash 控制器解鎖、擦除才能寫
- 對照：`s_test_count`（RAM）可以改；`const` 區域變數在 stack（RAM），debugger 也改得動
- 除錯應用：程式寫入某指標時當機 → 先看指標值是不是 `0x0800xxxx`

### [解法] 2026-11-18 22:45

【解法】各種變數放在哪裡：用 .map、debugger、size 驗證
**有初值的全域／static → .data（Flash 存初值、RAM 放變數）；沒初值 → .bss（RAM）；const 全域 → .rodata（只在 Flash）；一般區域 → stack（RAM）**

測試程式（`main.c`）
```c
volatile uint32_t g_test_data = 0x12345678U;          // 有初值的全域
volatile uint32_t g_test_bss;                         // 沒初值的全域
const volatile uint32_t g_test_const = 0xCAFEBABEU;   // const 全域
volatile uint32_t g_test_sink;

void Test_Storage(void)
{
    static uint32_t s_test_count = 0xAABBCCDDU;        // static 區域，有初值
    static uint32_t s_test_zero;                       // static 區域，沒初值
    volatile uint32_t test_local = 0x55667788U;        // 一般區域
    ...
}
```

觀察紀錄
| 變數 | 預期 | `.map` 區段 | 實際位址 | 結論 |
|---|---|---|---|---|
| `g_test_data` | .data | `.data` | `0x20000000`（初值 `0x080006B0`） | 兩邊都有 |
| `g_test_const` | .data（錯） | `.rodata` | `0x080006A4` | 只在 Flash |
| `s_test_count` | stack（錯） | `.data.s_test_count.1` | `0x20000004`（初值 `0x080006B4`） | 和全域一樣 |
| `s_test_zero` | stack（錯） | `.bss.s_test_zero.0` | `0x2000003C` | RAM |
| `g_test_sink` | — | `.bss` | `0x20000038` | RAM |
| `test_local` | stack | 找不到 | `0x20004FCC`（`sp + 4`） | stack；初值 `0x55667788` 在指令後的常數區 |

總表（必學）
| 宣告 | 區段 | Flash | RAM | 誰放進去 |
|---|---|---|---|---|
| 有初值的全域變數 | `.data` | 初值 | 變數 | Reset_Handler 複製 |
| 沒初值（或 = 0）的全域變數 | `.bss` | — | 變數 | Reset_Handler 清 0 |
| `const` 全域變數 | `.rodata` | 值 | — | 燒錄時就在 |
| `static` 區域變數 | 同全域（`.data`／`.bss`） | 有初值才有 | 變數 | 同全域 |
| 一般區域變數 | stack | 初值在指令裡 | 變數 | 函式執行時寫入 |
| 程式碼 | `.text` | 有 | — | 燒錄時就在 |

用量計算（`arm-none-eabi-size` 的 `text data bss`）
| 欄位 | 內容 | 本專案 |
|---|---|---|
| `text` | 向量表、程式碼、`.rodata` | 1712 |
| `data` | `.data`（兩邊都佔） | 8 |
| `bss` | `.bss` + `._user_heap_stack` 預留 | 1592 |

- Flash = `text` + `data`；RAM = `data` + `bss`；`dec` 是三欄總和，不是任何一種記憶體的用量
- Build Analyzer 的 KB = 1024 byte：RAM 1600 byte = 1.56 KB（7.81%）、Flash 1716 byte = 1.68 KB（2.62%），和手算一致

查法
- `.map`：搜尋變數名稱（static 用片段搜尋，名字會加 `.0`、`.1`）；先確認不在 `Discarded input sections` 段落
- debugger：Expressions 視窗輸入 `&變數名稱`；區域變數只有停在該函式裡才看得到
- 位址開頭：`0x0800` = Flash、`0x2000` = RAM
- 位址要等連結完成才知道，編譯前只能預測在哪一區

### [問題] 2026-11-18 23:06

【問題】以為 main() 裡宣告的變數會受 .data 影響
**main() 裡的變數是一般區域變數，放在 stack，初值寫在指令裡；main 不結束也一樣是 stack**

- 錯在哪：以為 `uint32_t led_period = 500U;` 這類 main() 裡的變數放在 .data，拿掉複製 .data 會讓 LED 壞掉
- 正確：沒有 `static` 的區域變數都在 stack，不管是不是在 main()
- S04 的模組沒有「初值非 0」的全域／static 變數 → 加測試變數前 .data 是 0 byte
- 只有「全域或 static」且「初值不是 0」的變數才在 .data

### [筆記] 2026-11-18 23:06

【筆記】冷開機錯、按 reset 就正常：懷疑 .data／.bss 初始化
**reset 鍵不會清 RAM，殘留值可能掩蓋「從沒被正確初始化」的 bug；冷開機才會露出來**

| | 上電（冷開機） | reset 鍵（熱重置） |
|---|---|---|
| RAM 內容 | 亂碼 | 保留上次執行的值 |
| .data 複製壞掉時 | 錯 | 看起來正常 |

- 優先檢查：Reset_Handler 的複製 .data 迴圈、`.ld` 的 `.data` 是否 `>RAM AT> FLASH`、`_sidata = LOADADDR(.data)`
- 用 debugger 測試時也一樣：重新開始 ≠ 斷電，要先把 RAM 填成 `DEADBEEF` 才看得出差別

### [解法] 2026-11-19 21:46

【解法】故意弄壞：拿掉複製 .data 的迴圈
**拿掉複製迴圈後，有初值的全域／static 變數變成 RAM 裡的亂碼；.bss 和 stack 上的變數不受影響**

做法
- `startup_stm32f103c8tx.s`：把 `ldr r0, =_sdata` 到 `bcc CopyDataInit` 用 `/* */` 包起來（第 63 行原本的註解之後才開始包，避免註解交錯）
- 停在 `Reset_Handler`，Memory 視窗（Hex Integer）把 4 個位址填成 `DEADBEEF`，模擬上電亂碼
- 中斷點設在 `main()` 的 `Test_Storage();`，按 F8

觀察紀錄
| 位址 | 變數 | 區段 | 預期 | 實際 | 結論 |
|---|---|---|---|---|---|
| `0x20000000` | `g_test_data` | .data | `DEADBEEF` | `DEADBEEF` | 沒被複製，保持亂碼 |
| `0x20000004` | `s_test_count` | .data | `DEADBEEF` | `DEADBEEF` | static 區域變數一樣受影響 |
| `0x20000034` | `g_test_bss` | .bss | 0 | 0 | 清 .bss 照常 |
| `0x2000003C` | `s_test_zero` | .bss | 0 | 0 | 清 .bss 照常 |
| — | LED／按鍵 | stack、.bss | 正常 | 正常 | S04 沒有初值非 0 的全域變數 |

結論
- 只有「全域或 static」且「初值不是 0」的變數依賴複製 .data
- main() 裡的區域變數（`led_period = 500U` 等）在 stack，初值寫在指令裡，不受影響
- 用 debugger 時，在 main() 裡看不到 static 區域變數的名字（顯示 Error）→ 改用 `.map` 查位址，在 Memory 視窗看
- 實驗後要恢復啟動檔

### [筆記] 2026-11-19 22:17

【筆記】push {r7, lr}：函式開頭存返回位址和 frame pointer
**會呼叫別人的函式要先把 LR（返回位址）存到 stack；-O0 時 r7 是找區域變數的基準，也要存起來**

- `Stack_Eater()` 開頭：`push {r7, lr}`（8 byte）+ `sub sp, #64`（`buf[16]`）= 每層 72 byte
- LR：`bl` 會覆蓋 LR，函式裡還要呼叫別人 → 先存自己的返回位址，否則回不去
- r7：-O0 時用來定位區域變數（`add r7, sp, #0`）；呼叫者也在用，要還原
- 遞迴每一層都會再吃一次 72 byte，永不返回就一直往下長

### [問題] 2026-11-19 22:18

【問題】以為 volatile 會影響變數放在哪個區段
**volatile 只要求編譯器每次真的去讀寫記憶體，不影響位置；位置由 const、static、全域、初值決定**

- 錯在哪：以為 `volatile uint32_t g_depth;` 會在 `.rodata`
- 原因：上次 `const volatile` 的變數在 `.rodata`，把功勞算給 volatile
- 正確：
| 關鍵字 | 決定什麼 |
|---|---|
| `const`（全域） | 放 `.rodata`（Flash） |
| 全域／`static` + 有初值 | `.data` |
| 全域／`static` + 沒初值 | `.bss` |
| `volatile` | 不准最佳化掉讀寫，跟位置無關 |
- `g_depth` 是沒初值的全域 → `.bss.g_depth` 在 `0x2000003C`

### [問題] 2026-11-19 22:18

【問題】以為執行時有機制會擋住 stack overflow
**`._user_heap_stack` 只在連結時檢查一次；執行時編譯器、連結器、CPU 都不檢查 SP，stack 會安靜地蓋掉 .bss、.data**

- 錯在哪：以為「heap 和 stack 之間要留固定空間」會在執行時擋住
- 正確：
| 機制 | 何時 | 檢查什麼 |
|---|---|---|
| `._user_heap_stack` | 連結時 | .data + .bss 後面留不留得下 heap + stack 的最小值 |
| `_sbrk()`（`sysmem.c`） | `malloc` 時 | heap 有沒有長進 stack 保留區 |
| 執行時的 SP | — | 沒有任何檢查 |
- `.rodata` 在 Flash，stack 寫不進去，不會被蓋掉
- 危險：全域變數被安靜地改壞，程式行為怪異，但不會馬上當機

### [筆記] 2026-11-19 22:33

【筆記】volatile 讀寫的「記憶體」：變數本身所在的位址
**volatile 要求每次回到變數的原位址讀寫，不准只用 CPU 暫存器裡的副本；位址在 RAM、Flash 或周邊暫存器都一樣**

| 變數 | 位址 | 讀寫對象 |
|---|---|---|
| 一般全域變數 | `0x2000xxxx` | RAM |
| `const volatile` 全域 | `0x0800xxxx` | Flash（唯讀） |
| `GPIOC->ODR`（`__IO` = `volatile`） | `0x4001xxxx` | 周邊暫存器 |

- 對比的是 CPU 暫存器（r0–r12）：沒有 volatile，編譯器可能讀一次就一直用暫存器裡的副本
- MCU 兩大用途：周邊暫存器（硬體會改值）、中斷與主程式共用的變數

### [待學] 2026-11-19 22:37

【待學】HardFault 完整分析（CFSR／HFSR 各 bit、從 stack frame 找出當機那一行、寫自己的 HardFault_Handler）：學中斷與例外時再學

### [待學] 2026-11-19 22:37

【待學】stack overflow 的偵測方法（stack painting 填固定值檢查用量、把 stack 放到 RAM 底部讓溢位立刻 fault、CubeIDE 的 Static Stack Analyzer）：之後做專案時再學

### [解法] 2026-11-19 22:43

【解法】故意弄壞：無限遞迴造成 stack overflow
**stack 往下長，安靜地蓋掉 .bss、.data；SP 掉出 RAM 後寫入保留區 → bus error → 升級成 HardFault → 停在 Default_Handler**

測試程式（實驗後要拿掉 `Stack_Eater();`）
```c
volatile uint32_t g_depth;              // .bss，0x2000003C

void Stack_Eater(void)
{
    volatile uint32_t buf[16];          // 每層 64 byte
    buf[0] = g_depth;
    g_depth++;
    Stack_Eater();
    buf[1] = buf[0];                    // 避免編譯器把遞迴改成迴圈
}
```

每層大小（`.list`）
- `push {r7, lr}`（8 byte：呼叫者的 r7、返回位址 lr）+ `sub sp, #64`（`buf`）= 72 byte
- 預估：`(0x20004FD0 − 0x20000044) ÷ 72 ≈ 283` 層撞進 .bss

觀察紀錄
| 觀察的東西 | 預期 | 實際 | 結論 |
|---|---|---|---|
| 第 280 層的 `sp` | 約 `0x200000D0` | `0x200000D0` | 每層 72 byte 正確 |
| 第 280 層的 `g_depth`、`g_test_data` | 280、`12345678` | `0x118`、`12345678` | 還沒撞到 |
| 最後 PC | — | `Infinite_Loop`（`Default_Handler`） | 沒寫 HardFault_Handler，weak 指向 Default_Handler |
| 最後 `sp` | — | `0x1FFFFFD8` | 已掉出 RAM（`< 0x20000000`） |
| 最後 `g_depth` | 不可信 | `0x0800056B` | 被 push 的 lr（返回位址 + 1）蓋掉 |
| 最後 `g_test_data` | 被蓋掉 | `12345678` | 剛好落在 buf 沒寫到的位置，幸運保住 |
| CFSR `0xE000ED28` | — | `0x00001400` | STKERR（bit 12）+ IMPRECISERR（bit 10） |
| HFSR `0xE000ED2C` | — | `0x40000000` | FORCED（bit 30）：其他 fault 升級成 HardFault |
| Debugger Console | — | `Could not fetch required XPSR content. Further unwinding is impossible.` | stack 在無效位址，GDB 讀不到呼叫堆疊 |

當機過程
| 順序 | 發生什麼 |
|---|---|
| 1 | 遞迴每層吃 72 byte，SP 一路往下，經過空的 heap 區 |
| 2 | 第 283 層：push 把 r7、lr 寫到 `0x20000038`（`g_test_sink`）、`0x2000003C`（`g_depth`） |
| 3 | `buf[0]` 寫到 `0x1FFFFFF8`（保留區）→ bus error（IMPRECISERR，寫入有緩衝所以不精確） |
| 4 | BusFault 沒開啟 → 升級成 HardFault（FORCED） |
| 5 | 進 HardFault 時存 8 個暫存器到 `0x1FFFFFD8` 也失敗（STKERR） |
| 6 | 向量表的 HardFault 指向 `Default_Handler` → 無窮迴圈 |

結論（面試版）
- stack overflow 時，編譯器、連結器、CPU 都不會攔；stack 先安靜地蓋掉 .bss、.data 的變數，程式行為變怪
- 被蓋掉的是「剛好寫到的位置」，哪個變數壞掉不固定 → 很難重現
- SP 掉出 RAM 才會 fault：bus error → HardFault，停在 Default_Handler
- 除錯判斷：卡在 HardFault／Default_Handler 時先看 `sp`，不在 `0x20000000`～`0x20005000` 或貼近 RAM 底部，加上 CFSR 有 STKERR → 懷疑 stack overflow
- 全域變數出現 `0x0800xxxx` 的奇數 → 很可能被 stack 上的返回位址蓋掉
- Memory 視窗看暫存器要用 Hex Integer，逐 byte 顯示會看反

### [問題] 2026-11-24 13:35

【問題】把 Reset_Handler 裡的動作都當成硬體做的
**硬體只做「讀向量表前兩格 → SP、PC」；之後設 SP、SystemInit、複製 .data、清 .bss、呼叫 main 都是啟動程式（startup_*.s）的指令**

- 錯在哪：流程圖從 Reset_Handler 起全部標成【硬體】
- 分辨方法：有沒有對應的指令？debugger 單步時按 F5 走得過去的，就是軟體
| 誰做的 | 包含 |
|---|---|
| 硬體（無指令，重置時自動發生） | 從 `0x00000000` 讀 SP、從 `0x00000004` 讀 PC、設 T bit |
| 啟動程式（`startup_*.s`） | 設 SP、`bl SystemInit`、複製 .data、清 .bss、`bl __libc_init_array`、`bl main` |
| 我的程式 | `main()` 之後 |
- 意義：啟動程式可以改（本課註解掉複製迴圈就是改它），硬體行為不能改
- 面試：「誰把 .data 搬到 RAM？」→ 啟動程式的 Reset_Handler，不是硬體

### [筆記] 2026-11-24 13:36

【筆記】上電到 main() 流程圖
**硬體只讀向量表前兩格（SP、PC）；之後由啟動程式設 SP、複製 .data、清 .bss，準備好 C 執行環境才呼叫 main()**

```
上電／reset（BOOT0 = 0 → Flash 映射到 0x00000000）
  │
  ├─【硬體】讀 0x00000000 的第一個 word
  │         → MSP = 0x20005000（_estack = RAM 起點 + 20 KB）
  │
  ├─【硬體】讀 0x00000004 的第二個 word（0x08000589）
  │         → bit 0 = 1 → xPSR 的 T bit（Thumb 狀態）
  │         → 其餘 → PC = 0x08000588（Reset_Handler）
  │
  ├─【啟動程式】ldr r0, =_estack / mov sp, r0
  │         → 再設一次 SP（從 bootloader 跳進來、debugger 直接設 PC 時，硬體不會讀向量表）
  │
  ├─【啟動程式】bl SystemInit
  │         → 本專案是 nop.w（.weak 但沒有定義）
  │         → 這時全域變數還是亂碼，只能寫暫存器、用區域變數
  │
  ├─【啟動程式】複製 .data
  │         → 從 _sidata（Flash 0x080006B0）複製到 _sdata～_edata（RAM 0x20000000～0x20000008）
  │
  ├─【啟動程式】清 .bss
  │         → _sbss～_ebss（RAM）全部寫 0
  │
  ├─【啟動程式】bl __libc_init_array（C 函式庫初始化）
  │
  ├─【啟動程式】bl main
  │
  └─【我的程式】main()：Clock_Init() → BSP_SysTick_Init() → BSP_GPIO_Init() → 主迴圈
                 （main 若返回 → 啟動程式的 LoopForever 無窮迴圈）
```

為什麼是這個順序
| 先 | 後 | 原因 |
|---|---|---|
| 硬體載入 SP | 任何指令 | 函式呼叫、中斷都要用 stack |
| 設 SP | SystemInit | SystemInit 是 C 函式，用 stack |
| SystemInit | 複製 .data | 可能要先初始化放 .data 的外接記憶體；先把時脈調快 |
| 複製 .data、清 .bss | main | C 語言保證 main 開始時全域變數已是初值或 0 |

關鍵位址（本專案實測）
| 符號 | 位址 | 在哪 |
|---|---|---|
| `_estack` | `0x20005000` | RAM 頂端 |
| `Reset_Handler` | `0x08000588`（會隨程式變動） | Flash |
| `_sidata` | `0x080006B0`（會隨程式變動） | Flash |
| `_sdata`／`_edata` | `0x20000000`／`0x20000008` | RAM |
| `_sbss`／`_ebss` | `0x20000008`／`0x20000044` | RAM |

### [面試] 2026-11-24 14:35

【面試】STM32 上電後、執行第一條指令前，CPU 做了什麼？BOOT0 扮演什麼角色？
**硬體從 0x00000000 讀 MSP、從 0x00000004 讀 Reset_Handler 位址載入 PC；BOOT0 決定 0x00000000 映射到哪塊記憶體**

重置後，硬體先從 `0x00000000` 讀第一個 word 載入 MSP，再從 `0x00000004` 讀第二個 word 當作 Reset_Handler 的位址。這個值的 bit 0 必須是 1，代表 Thumb 狀態，會放進 xPSR 的 T bit，其餘放進 PC。這兩件事沒有任何指令，是硬體自動做的。BOOT0 決定 `0x00000000` 映射到哪塊記憶體：BOOT0 = 0 時是主 Flash（`0x08000000`），跑自己的程式；BOOT0 = 1、BOOT1 = 0 時是系統記憶體，跑 ST 的 bootloader。

| 項目 | 本專案實測 |
|---|---|
| `0x00000000` 的值 → MSP | `0x20005000`（`_estack`） |
| `0x00000004` 的值 | `0x08000589` |
| PC | `0x08000588`（Reset_Handler） |
| xPSR | `0x01000000`（T bit = 1） |

可能的追問：向量表的值 bit 0 如果是 0 會怎樣？（CPU 想切到 ARM 狀態，Cortex-M3 不支援 → HardFault）

### [面試] 2026-11-24 14:36

【面試】Reset_Handler 從開始到 main() 做了哪些事？
**設 SP → SystemInit → 複製 .data → 清 .bss → __libc_init_array → main，目的是在 main 之前把 C 執行環境準備好**

Reset_Handler 先把 SP 設成 `_estack`。硬體雖然已經設過，但從 bootloader 跳進來時硬體不會讀向量表，所以保險再設一次。接著呼叫 SystemInit 做晶片初始化，這時全域變數還沒準備好，只能寫暫存器。然後把 .data 的初值從 Flash 的 `_sidata` 複製到 RAM 的 `_sdata` 到 `_edata`，再把 `_sbss` 到 `_ebss` 清成 0。因為 C 語言保證 main 開始時全域變數已經是初值或 0，所以這兩步一定要在 main 之前做完。最後呼叫 `__libc_init_array`，再進 main。這些都是 `startup_*.s` 的指令，不是硬體做的。

| 動作 | 用到的符號 |
|---|---|
| 設 SP | `_estack` |
| 複製 .data | `_sidata`（來源，Flash）、`_sdata`～`_edata`（目的，RAM） |
| 清 .bss | `_sbss`～`_ebss` |

- 本專案的 `bl SystemInit` 被換成 `nop.w`：`.weak SystemInit` 沒有定義，時脈改由 main 裡的 `Clock_Init()` 設定

可能的追問：為什麼不需要 `_eidata`？（Flash 和 RAM 兩份長度一樣，用 `_edata − _sdata` 就算得出來）

### [面試] 2026-11-24 14:36

【面試】.text、.rodata、.data、.bss、heap、stack 各放在哪裡？
**.text、.rodata 在 Flash；.data、.bss、heap、stack 在 RAM，其中 .data 的初值另外存在 Flash**

程式碼 .text 和常數 .rodata 放在 Flash，斷電保留。RAM 由低到高依序是 .data、.bss、heap、stack。.data 比較特別：變數在 RAM，初值存在 Flash，上電時由 Reset_Handler 複製過去。heap 從 .bss 後面往上長，stack 從 RAM 頂端往下長，兩者之間是空閒空間，撞在一起就是 overflow。

| 區段 | Flash | RAM | 成長方向 |
|---|---|---|---|
| `.text` | ✅ | | |
| `.rodata` | ✅ | | |
| `.data` | 初值 | 變數 | |
| `.bss` | | ✅ | |
| heap | | ✅ | 往上 |
| stack | | ✅（頂端 `0x20005000`） | 往下 |

可能的追問：為什麼 stack 放在 RAM 頂端？（和往上長的 heap 往中間長，空間利用最大）

### [面試] 2026-11-24 14:37

【面試】怎麼知道某個全域變數的位址？怎麼算 Flash 和 RAM 用了多少？
**位址看 .map（或 debugger 的 &變數）；用量看 size 的 text、data、bss：Flash = text + data，RAM = data + bss**

在 `.map` 搜尋變數名稱，先確認它不在開頭的 `Discarded input sections` 段落（那裡位址都是 0，代表被連結器丟掉了），再看它在哪個輸出區段、位址多少。`0x0800` 開頭是 Flash，`0x2000` 開頭是 RAM。static 變數名字會被加上 `.0`、`.1`，要用片段搜尋。用量看編譯完 Console 印出的 `text data bss`：Flash 等於 text 加 data，因為 .data 的初值也存在 Flash；RAM 等於 data 加 bss，bss 這一欄已經包含 heap 和 stack 的預留空間。`dec` 是三欄總和，不是任何一種記憶體的用量。

| 欄位 | 本專案 | 算進 |
|---|---|---|
| `text` | 1712 | Flash |
| `data` | 8 | Flash + RAM |
| `bss` | 1592 | RAM |
| 結果 | Flash 1720 byte、RAM 1600 byte | Build Analyzer 一致（KB = 1024 byte） |

- `.ld` 的角色：`MEMORY` 定義 Flash、RAM 的起點和大小，`SECTIONS` 決定區段放哪；`.map` 是連結器照 `.ld` 排完的結果
- 位址要連結完才知道，程式一改就會移動

可能的追問：`.ld` 裡 `>RAM AT> FLASH` 是什麼意思？（執行位址在 RAM，載入位址在 Flash，只有 .data 這樣寫）

### [面試] 2026-11-24 14:39

【面試】有初值的全域變數、const、static 區域變數、一般區域變數分別放在哪？
**有初值全域 → .data；const 全域 → .rodata 只在 Flash；static 區域同全域；一般區域 → stack**

有初值的全域變數放在 .data，初值存在 Flash、變數在 RAM，上電時複製。const 全域變數的值不會變，不需要 RAM 副本，放在 .rodata，只在 Flash，debugger 也改不了它。static 區域變數的壽命和整個程式一樣長，所以和全域變數放在同一個地方，有初值就在 .data，沒有就在 .bss，差別只在名字只有函式內看得到。一般區域變數放在 stack，初值寫在函式的指令裡，每次呼叫才寫進去。

判斷順序：
| 問題 | 是 → |
|---|---|
| 沒有 static 的區域變數？ | stack |
| 全域且有 const？ | `.rodata`（只在 Flash） |
| 全域或 static，初值不是 0？ | `.data`（兩邊） |
| 全域或 static，沒初值或 = 0？ | `.bss`（RAM） |

| 本專案實測 | 位址 |
|---|---|
| `g_test_data`（有初值全域） | `0x20000000`，初值在 `0x080006B0` |
| `g_test_const`（`const volatile`） | `0x080006A4` |
| `s_test_count`（static 有初值） | `0x20000004` |
| `test_local`（區域） | `0x20004FCC`（stack） |

- `volatile` 不影響位置，只要求每次真的去讀寫

可能的追問：const 全域沒加 volatile 時，`.map` 為什麼找不到？（編譯器直接把值寫進指令，變數沒人引用，被 `--gc-sections` 丟掉）

### [面試] 2026-11-24 14:42

【面試】stack overflow 會發生什麼事？為什麼難除錯？怎麼判斷？
**先安靜地蓋掉 .bss、.data 的變數，SP 掉出 RAM 後才 HardFault；壞掉的變數看當下寫到哪裡，所以難重現**

stack 往下長，執行時沒有任何機制檢查 SP，編譯器、連結器、CPU 都不會攔。第一階段，stack 安靜地蓋掉 .bss、.data 的全域變數，程式繼續跑，只是行為變怪。第二階段，SP 掉出 RAM，寫入保留區產生 bus error，升級成 HardFault，停在 Default_Handler。難除錯是因為被蓋掉的只有「剛好寫到的位置」，哪個變數壞掉不固定，症狀還會出現在別的功能上。判斷方法：卡在 HardFault 時先看 SP，不在 RAM 範圍內或貼近底部，加上 CFSR 的 STKERR 是 1，就懷疑 stack overflow；全域變數出現 `0x0800` 開頭的奇數，通常是被 stack 上的返回位址蓋掉。

| 實驗觀察 | 值 |
|---|---|
| 每層遞迴 | 72 byte（`push {r7, lr}` + `sub sp, #64`） |
| 最後 `sp` | `0x1FFFFFD8`（已掉出 RAM） |
| `g_depth` | `0x0800056B`（被返回位址蓋掉） |
| `g_test_data` | `12345678`（剛好沒被寫到，倖存） |
| CFSR | `0x00001400`：STKERR + IMPRECISERR |
| HFSR | `0x40000000`：FORCED |

- `._user_heap_stack` 只在連結時檢查一次，執行時不管

可能的追問：怎麼預防或提早發現？（估算最大 stack 用量、stack painting、把 stack 放到 RAM 底部讓溢位立刻 fault）

### [問題] 2026-11-24 14:43

【問題】以為 stack overflow 難除錯是因為「寫入失敗、原值沒被覆蓋」
**難除錯是因為 stack 寫入 RAM 時是成功的：它安靜地改壞了剛好寫到的變數，哪個壞掉不固定，症狀出現在別處**

- 錯在哪：把第二階段（SP 掉出 RAM、寫入失敗）當成難除錯的原因
- 正確：第一階段寫入都成功，沒有任何錯誤訊號；被蓋掉的是「當下 stack 剛好寫到的位置」
- 實驗證據：`g_depth` 被返回位址蓋成 `0x0800056B`，`g_test_data` 卻剛好落在 `buf` 沒寫到的地方而倖存
- 症狀出現在別的功能上（例如 tick 變數壞掉 → LED 閃錯），容易查錯方向

### [面試] 2026-11-24 16:19

【面試】加了一個有初值的大陣列後 RAM 快不夠，你怎麼確認它放在哪、佔多少？size 的哪幾欄會變？
**在 .map 找到它在 .data；size 只有 data 欄 +2048，Flash 和 RAM 各多 2048 byte；初值非 0 才會連 Flash 也一起吃**

例子：`uint8_t buffer[2048] = {1};`（全域）

在 `.map` 搜尋 `buffer`，先確認它不在 `Discarded input sections`，再看它在哪個輸出區段：因為有非 0 的初值，會在 `.data` 底下，位址 `0x2000` 開頭，大小 `0x800`。`size` 輸出只有 `data` 欄增加 2048，`text` 和 `bss` 不變。Flash 等於 `text + data`，多 2048；RAM 等於 `data + bss`，也多 2048。重點是：初值只有第一個是 1，其餘 2047 個都是 0，卻還是要在 Flash 存一整份 2048 byte 的初值。如果改成 `= {0}` 或不給初值，它會進 `.bss`，Flash 一個 byte 都不加，只佔 RAM。

| 宣告 | 區段 | `text` | `data` | `bss` | Flash | RAM |
|---|---|---|---|---|---|---|
| `= {1}` | `.data` | — | +2048 | — | +2048 | +2048 |
| `= {0}` 或不給初值 | `.bss` | — | — | +2048 | — | +2048 |
| `const ... = {1}` | `.rodata` | +2048 | — | — | +2048 | — |

可能的追問：如果這個陣列內容永遠不會改呢？（加 `const` → `.rodata`，只佔 Flash，RAM 完全不用）

### [面試] 2026-11-24 16:19

【面試】自己幫新晶片寫 Reset_Handler，要放哪些步驟？清 .bss 和呼叫 main 對調會怎樣？
**設 SP → SystemInit → 複製 .data → 清 .bss → 呼叫 __libc_init_array → 呼叫 main；對調的話 .bss 永遠不會被清，全域變數初值是亂碼**

步驟依序是：設 SP（`_estack`）、呼叫 SystemInit 做晶片初始化、把 .data 從 `_sidata` 複製到 `_sdata`～`_edata`、把 `_sbss`～`_ebss` 清成 0、呼叫 `__libc_init_array`、最後呼叫 main。如果把清 .bss 放到呼叫 main 之後，因為裸機的 main 是永遠不返回的無窮迴圈，清 .bss 根本不會執行到。所有「沒有初值、C 語言保證是 0」的全域變數都會是 RAM 裡的亂碼。例如 tick 計數變數初值是亂碼，第一次算 `now - last` 就錯。更麻煩的是，這種錯只在冷開機出現，按 reset 鍵時 RAM 保留上次的值，看起來又正常。

| 步驟 | 用到 | 為什麼排在這裡 |
|---|---|---|
| 設 SP | `_estack` | 之後的 C 函式都要用 stack |
| SystemInit | — | 可能要先初始化放 .data 的記憶體；這時全域變數還不能用 |
| 複製 .data | `_sidata`、`_sdata`、`_edata` | main 之前完成 |
| 清 .bss | `_sbss`、`_ebss` | main 之前完成 |
| `bl __libc_init_array` | — | C 函式庫初始化，要用到全域變數 |
| `bl main` | — | C 執行環境已準備好 |

可能的追問：為什麼「只有冷開機錯、按 reset 就好」？（reset 鍵不會清 RAM，殘留值掩蓋了沒初始化的 bug）

### [面試] 2026-11-24 16:19

【面試】這段程式裡每個變數和函式放在哪裡？
**const 全域 → .rodata；沒初值全域 → .bss；有初值全域 → .data；static 依初值分 .data／.bss；一般區域 → stack；函式 → .text**

```c
const uint16_t sine_table[256] = { ... };   // .rodata，只在 Flash
uint32_t error_count;                       // .bss，只在 RAM
uint32_t baud_rate = 115200;                // .data，初值在 Flash、變數在 RAM

void UART_Task(void)                        // .text，Flash
{
    static uint8_t state = 0;               // .bss（初值 = 0 視同沒初值）
    static uint8_t retry = 3;               // .data
    uint8_t rx_byte = 0;                    // stack
}
```

先看是不是沒有 static 的區域變數，是的話放 stack。不是的話，全域有 const 就放 `.rodata`，只在 Flash；初值不是 0 放 `.data`，兩邊都有；沒初值或初值是 0 放 `.bss`，只在 RAM。函式的程式碼放在 `.text`，在 Flash。`.ld` 規定 `.text` 放進 FLASH，實際位址看 `.map` 裡的 `.text.UART_Task`。

| 宣告 | 區段 | Flash | RAM |
|---|---|---|---|
| `const` 全域 | `.rodata` | ✅ | |
| 全域／static，初值非 0 | `.data` | 初值 | 變數 |
| 全域／static，沒初值或 = 0 | `.bss` | | ✅ |
| 一般區域 | stack | 初值在指令裡 | ✅ |
| 函式 | `.text` | ✅ | |

- 例外：標成 `.RamFunc` 的函式會複製到 RAM 執行（例如擦寫 Flash 時）

可能的追問：`sine_table` 拿掉 const 會怎樣？（變成 `.data`，Flash 和 RAM 各多 512 byte）

### [面試] 2026-11-24 16:19

【面試】設定值莫名變成 0x08001A2F，過一陣子才當機，同事說是指標寫錯，你怎麼看？
**先懷疑 stack overflow：0x0800 開頭的奇數是 push 到 stack 的返回位址；先改壞、後當機也符合 stack overflow 的兩個階段**

`0x08001A2F` 是 Flash 位址，代表程式碼的位置；它是奇數，bit 0 是 Thumb bit。RAM 裡出現「程式碼位址 + 1」，通常是 `bl` 存進 LR、再被 `push {lr}` 存到 stack 的返回位址。一般寫錯的指標很少剛好寫出這種值，所以我會先懷疑 stack 長到這個變數的位置了。「先改壞、過一陣子才當機」也符合 stack overflow：先安靜地蓋掉全域變數，SP 掉出 RAM 才 HardFault。

| 順序 | 檢查什麼 | 看哪裡 |
|---|---|---|
| 1 | 去掉 bit 0 得 `0x08001A2E`，反查是哪個函式的返回點 | `.list` |
| 2 | 被蓋的變數在 RAM 哪裡（通常在 .bss／.data 最高處） | `.map` |
| 3 | 找吃 stack 的地方：遞迴、大區域陣列、深呼叫鏈、中斷巢狀 | 程式碼、`.list` 的 `sub sp` |
| 4 | 當機時 `sp` 是否掉出 RAM、CFSR 的 STKERR | Registers、`0xE000ED28` |
| 5 | 修正：加大 `_Min_Stack_Size`、大區域陣列改 `static`、減少呼叫深度 | `.ld`、程式碼 |

可能的追問：為什麼返回位址是奇數？（Cortex-M3 只能跑 Thumb 指令，跳轉位址用 bit 0 = 1 表示 Thumb 狀態）

### [問題] 2026-11-24 16:19

【問題】把有初值的全域變數說成放在 .bss
**兩邊都有的只有 .data；.bss 只在 RAM，用來放沒初值或初值為 0 的變數**

- 錯在哪：重考時寫 `uint32_t baud_rate = 115200;` 放在「Flash 和 RAM 的 bss」
- 正確：有非 0 初值 → `.data`（初值在 Flash、變數在 RAM）
- 記法：`.bss` 不需要從 Flash 搬東西，只要清 0，所以 Flash 裡沒有它的任何資料

### [問題] 2026-11-24 16:20

【問題】把 Reset_Handler 呼叫 main 說成「連接 main」
**連接（link）是編譯時連結器做的事；Reset_Handler 在執行時做的是呼叫（bl）**

- 錯在哪：步驟寫成「連接 C 函式庫 → 連接 main → 呼叫 main」
- 正確：「呼叫 `__libc_init_array` → 呼叫 main」，`bl main` 只有一步
| 時期 | 誰做 | 做什麼 |
|---|---|---|
| 編譯時 | 連結器 | 依 `.ld` 排位址、產生 `.map`、丟掉沒用到的區段 |
| 執行時 | Reset_Handler | 用 `bl` 呼叫 SystemInit、`__libc_init_array`、main |

### [筆記] 2026-11-24 16:20

【筆記】全域變數變成 0x0800 開頭的奇數：stack overflow 的指紋
**0x0800 開頭 = 程式碼位址，奇數 = Thumb bit；RAM 裡出現它，幾乎一定是 stack 上 push 的返回位址（LR）**

- 來源：`bl` 把返回位址（+1，Thumb bit）放進 LR → 函式開頭 `push {..., lr}` 存進 stack
- 一般寫錯的指標很少剛好寫出「程式碼位址 + 1」；會寫進返回位址的正常只有 stack
- 實驗證據：`g_depth` 被蓋成 `0x0800056B`

排查順序
| 順序 | 做什麼 | 看哪裡 |
|---|---|---|
| 1 | 值去掉 bit 0，反查是哪個函式的返回點 | `.list` 搜尋該位址 |
| 2 | 確認被蓋的變數在 RAM 的位置（通常在 .bss／.data 最高處） | `.map` |
| 3 | 找吃 stack 的元兇：遞迴、大區域陣列、深呼叫鏈、中斷巢狀 | 程式碼、`.list` 的 `sub sp` |
| 4 | 當機時的證據：`sp` 是否掉出 RAM、CFSR 的 STKERR | Registers、Memory `0xE000ED28` |
| 5 | 修正：加大 `_Min_Stack_Size`、大區域陣列改 `static`、減少呼叫深度 | `.ld`、程式碼 |

面試版：「設定值被改成 0x0800 開頭的奇數，我會先懷疑 stack overflow，因為那是 push 到 stack 的返回位址；再用 .list 反查是哪個函式，用 .map 確認變數位置。」

### [面試] 2026-11-24 16:40

【面試】區域變數宣告 4 KB 陣列，連結成功但執行時按鍵失靈、最後當機，為什麼？怎麼修？
**連結器只檢查 stack 的最小預留量，不知道函式執行時吃多少；陣列蓋進 .bss 造成雙向破壞；改成 static 讓連結器算進去**

連結器的檢查是 `.data + .bss + heap 最小值 + stack 最小值` 有沒有超過 RAM，這個例子是 16 + 0.5 + 1 = 17.5 KB，通過。但區域變數是執行時才在 stack 上配置的，連結器不知道 `UART_Task()` 一進去就要 4 KB。stack 頂端到 .bss 只剩大約 4 KB，陣列就和 .bss 重疊，造成雙向破壞：寫 `rx_buf` 會蓋掉全域變數，所以按鍵狀態被改壞；程式寫全域變數又會蓋掉 stack 上的返回位址，函式返回時跳到錯的地方，就 HardFault。確認方法是看 `.su` 檔或 `.list` 的 `sub sp` 算 stack 用量，再和 `_estack − _ebss` 比較。修法是改成 `static`，讓它進 .bss，空間不夠時連結就會失敗，把執行時的隨機當機變成編譯時的錯誤。

| 項目 | 數值 |
|---|---|
| 連結時檢查 | 16 + 0.5 + 1 = 17.5 KB ≤ 20 KB → 通過 |
| 實際可用 stack | `0x20005000 − 0x20004000` ≈ 4 KB |
| `rx_buf` | 4096 byte + 呼叫鏈其他 frame → 重疊 .bss |

| 破壞方向 | 症狀 |
|---|---|
| 寫 `rx_buf` → 蓋 .bss 變數 | 按鍵偶爾失靈 |
| 寫全域變數 → 蓋 stack 上的返回位址 | 返回時跳錯 → HardFault |

| 修法 | 效果 |
|---|---|
| `static uint8_t rx_buf[4096];` | 進 .bss，連結器算進去，不夠就 `region 'RAM' overflowed` |
| 縮小 buffer／加大 `_Min_Stack_Size` | 增加餘裕 |

可能的追問：怎麼知道每個函式吃多少 stack？（`Debug/Src/*.su` 檔、Static Stack Analyzer 視窗、`.list` 的 `sub sp, #N`）

### [問題] 2026-11-24 16:41

【問題】以為停在 Default_Handler 就代表「寫了唯讀區」
**Default_Handler 只代表發生了沒寫處理函式的例外，原因要看 CFSR／HFSR 才知道**

- 錯在哪：重考時說「停在 Default_Handler，代表可能想寫唯讀區」
- 正確：所有沒實作的例外（HardFault、各種中斷）都 weak 指向 Default_Handler，光看停在那裡無法判斷原因
- stack overflow 常見的兩種當機：SP 掉出 RAM 寫入保留區（STKERR）；返回位址被全域變數蓋掉，return 跳到錯的位址
- 判斷要看：`sp`、CFSR（`0xE000ED28`）、HFSR（`0xE000ED2C`）

### [問題] 2026-11-24 16:41

【問題】以為連結器不會檢查 RAM 剩餘空間
**連結器會檢查，但只檢查 .data + .bss + heap／stack 最小預留量；區域變數在執行時才配置，連結器看不到**

- 錯在哪：重考時說「連結器不會幫忙檢查剩餘大小」
- 正確：`._user_heap_stack` 會檢查，超過 RAM 會報 `region 'RAM' overflowed`；但 stack 只預留 `_Min_Stack_Size`，函式實際用多少它不知道
- 應用：大陣列改成 `static` 或全域 → 進 .bss → 連結器算得到，不夠時編譯就失敗
