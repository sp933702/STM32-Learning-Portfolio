# SPRINT-W01-S05：Startup 與 Linker Script

- 狀態：**進行中**
- 階段：基礎　主題：Startup
- 進行次數：6 次（最近一次：2026-11-16）
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
