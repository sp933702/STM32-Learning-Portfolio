# 面試準備

- 這一頁由學習進度 App 自動彙整，請不要直接修改；要改內容請到 App 改對應的筆記。
- 用法：先遮住答案自己講一次，再對照。講不順的課題回 App 按「複習」再考一次。
- 目前有面試卡 11 則、驗收回答與面試版說明 7 段。

## 基礎

### [SPRINT-W01-S01](notes/SPRINT-W01-S01.md) C 語言驗收

- 複習 0 次，已到複習日

其他提到面試的筆記（全文在這一課的筆記頁）：

- 【SPRINT-W01-S01／Q00】Data Model 與 ABI

### [SPRINT-W01-S02](notes/SPRINT-W01-S02.md) 時脈系統（暫存器）

- 複習 0 次，已到複習日

#### S02 驗收回答範本（面試用）

**SPRINT-W01-S02 驗收：四題的完整回答**

**1. 怎麼確認 SYSCLK 已切到 PLL？**
- 看 `RCC->CFGR` 的 SWS（bit 3:2）：`0x001D040A` 的最後一位 `0xA` = `1010`，SWS = `10` = PLL
- SW 是軟體寫入的「要求」，SWS 是硬體回報的「實際狀態」
- 不能只看函式回傳值：曾經寫錯暫存器，回傳成功但實際沒切換（㊾）

**2. 為什麼要先設 Flash latency？**
- Flash 讀取時間固定，約 41.7 ns（24 MHz 一個週期，所以 0 WS 最高 24 MHz）
- 72 MHz 一個週期 13.9 ns → 41.7 ÷ 13.9 ≈ 3 個週期 → WS = 3 − 1 = **2**
- 若先升頻：CPU 在 Flash 還沒準備好時取指令 → 讀到錯誤指令 → 程式亂跑或 HardFault
- 升頻先加 WS 再升頻，降頻先降頻再減 WS；WS 只能多不能少

**3. APB1 為什麼最高 36 MHz？**
- 出處：Datasheet 方塊圖，以及 RM0008 的 RCC_CFGR PPRE1 說明：軟體必須保證 APB1 不超過 36 MHz
- 屬硬體規格：APB1 上的周邊只依 36 MHz 設計與驗證，超過不保證正確運作
- 原因：頻率越高，功耗越大、時序收斂越難（36 MHz 週期 27.8 ns，72 MHz 只有 13.9 ns）
- 程式做法：**切換 SW 到 PLL 之前**先設好 APB1 ÷2，PCLK1 從 4 MHz 變成 36 MHz，全程在規格內

**4. 和 HAL 版的差異**
- timeout：HAL 用時間（`HAL_GetTick()`），自寫用圈數，會受時脈與編譯最佳化影響
- 切換過程：HAL 先把 APB 分頻暫設 ÷16，升降頻都安全；自寫只針對開機升頻
- 切換後：HAL 會更新 `SystemCoreClock` 並以 `HAL_InitTick()` 重設 SysTick
- HAL 會讀回檢查 latency；支援所有時脈源
- 自寫版簡短、每個 bit 都清楚，適合固定用途

其他提到面試的筆記（全文在這一課的筆記頁）：

- 把其他型號才有的周邊列成 C8 的

### [SPRINT-W01-S03](notes/SPRINT-W01-S03.md) GPIO（暫存器重做）

- 複習 0 次，已到複習日

其他提到面試的筆記（全文在這一課的筆記頁）：

- .h／.c 拆分原則
- RM0008 中文版與英文版節號對照
- 多行巨集為什麼要用 do { } while(0)

### [SPRINT-W01-S04](notes/SPRINT-W01-S04.md) SysTick 與 non-blocking（暫存器）

- 複習 0 次，已到複習日

#### 完成標準：32-bit 溢位時 (now - last) 仍正確（面試版）

**減法是在時鐘上算兩點距離，跨溢位仍正確；加法再比較是比絕對位置，溢位後基準就錯了**

- 減法：`now - last` = 從 last 走到 now 經過幾格，模 2³² 運算保證跨 0 仍正確，限制是間隔 < 49.7 天
- 加法：`now >= last + period` 比的是位置大小；繞圈時鐘上「誰比較大」沒有意義，`last + period` 溢位成小數字 → 判斷瞬間成立
- 實測：tick 初值 `0xFFFFF830`；加法寫法 1.5～2.0 s 瘋狂 toggle、溢位後卡住；減法寫法正常
- tick 要用無號數：C 的有號數溢位是未定義行為

**30 秒回答**
> tick 是 `uint32_t`，約 49.7 天溢位。判斷要寫 `now - last >= period`。無號數減法是模 2³² 運算，像在時鐘上算距離，繞回 0 後減出來仍是實際經過時間，只要間隔不超過一圈。`now >= last + period` 比的是絕對位置，`last + period` 一溢位就變小，判斷瞬間成立。我把 tick 初值設在溢位前 2 秒實測過，加法寫法溢位前 0.5 秒開始亂閃、之後卡住，減法寫法正常。

#### 面試版說明（出自「BSP_SysTick_GetTick() 與 volatile 的實驗驗證」）

- tick 在 SysTick 中斷加 1、主程式讀；編譯器不知道中斷會改它，可能只讀一次放 CPU 暫存器甚至整段刪除
- 實測 `-O2` 拿掉 `volatile`，延遲迴圈變成跳回自己的無窮迴圈；加回後每圈都有 `ldr` 重讀 SRAM
- `volatile` 不是關掉最佳化，而是禁止省略或快取對該變數的存取
- 限制：`volatile` 不保證原子性；這裡安全是因為 32 bit 讀取一道指令完成，且只有 ISR 寫

#### 面試版說明（出自「SPRINT-W01-S04 總整理：從頭到尾每一步」）

> 我只用 CMSIS 標頭檔設定 SysTick：LOAD 填 72 MHz 除以 1000 減 1，用 _Static_assert 確認不超過 24 bit；優先權設最低，VAL 清 0，最後 CTRL 選處理器時脈、開中斷、啟動。中斷裡讓 static volatile 的 tick 加 1，外部只能透過 GetTick 讀。volatile 我實測過，-O2 拿掉它延遲迴圈會變成無窮迴圈。主迴圈每圈取一次 now，LED 和按鍵去彈跳狀態機都用 now 減 last 判斷，無號數減法跨過 49.7 天的溢位仍正確，我把 tick 初值設在溢位前 2 秒驗證過。去彈跳用四個狀態，連續穩定 20 ms 才發事件，事件由使用者讀取時清除；邏輯分析儀量到從按下到反應 20.8 ms。

其他提到面試的筆記（全文在這一課的筆記頁）：

- 以為 press_event 要加 volatile

### [SPRINT-W01-S05](notes/SPRINT-W01-S05.md) Startup 與 Linker Script

#### STM32 上電後、執行第一條指令前，CPU 做了什麼？BOOT0 扮演什麼角色？

**硬體從 0x00000000 讀 MSP、從 0x00000004 讀 Reset_Handler 位址載入 PC；BOOT0 決定 0x00000000 映射到哪塊記憶體**

重置後，硬體先從 `0x00000000` 讀第一個 word 載入 MSP，再從 `0x00000004` 讀第二個 word 當作 Reset_Handler 的位址。這個值的 bit 0 必須是 1，代表 Thumb 狀態，會放進 xPSR 的 T bit，其餘放進 PC。這兩件事沒有任何指令，是硬體自動做的。BOOT0 決定 `0x00000000` 映射到哪塊記憶體：BOOT0 = 0 時是主 Flash（`0x08000000`），跑自己的程式；BOOT0 = 1、BOOT1 = 0 時是系統記憶體，跑 ST 的 bootloader。

| 項目 | 本專案實測 |
|---|---|
| `0x00000000` 的值 → MSP | `0x20005000`（`_estack`） |
| `0x00000004` 的值 | `0x08000589` |
| PC | `0x08000588`（Reset_Handler） |
| xPSR | `0x01000000`（T bit = 1） |

可能的追問：向量表的值 bit 0 如果是 0 會怎樣？（CPU 想切到 ARM 狀態，Cortex-M3 不支援 → HardFault）

#### Reset_Handler 從開始到 main() 做了哪些事？

**設 SP → SystemInit → 複製 .data → 清 .bss → __libc_init_array → main，目的是在 main 之前把 C 執行環境準備好**

Reset_Handler 先把 SP 設成 `_estack`。硬體雖然已經設過，但從 bootloader 跳進來時硬體不會讀向量表，所以保險再設一次。接著呼叫 SystemInit 做晶片初始化，這時全域變數還沒準備好，只能寫暫存器。然後把 .data 的初值從 Flash 的 `_sidata` 複製到 RAM 的 `_sdata` 到 `_edata`，再把 `_sbss` 到 `_ebss` 清成 0。因為 C 語言保證 main 開始時全域變數已經是初值或 0，所以這兩步一定要在 main 之前做完。最後呼叫 `__libc_init_array`，再進 main。這些都是 `startup_*.s` 的指令，不是硬體做的。

| 動作 | 用到的符號 |
|---|---|
| 設 SP | `_estack` |
| 複製 .data | `_sidata`（來源，Flash）、`_sdata`～`_edata`（目的，RAM） |
| 清 .bss | `_sbss`～`_ebss` |

- 本專案的 `bl SystemInit` 被換成 `nop.w`：`.weak SystemInit` 沒有定義，時脈改由 main 裡的 `Clock_Init()` 設定

可能的追問：為什麼不需要 `_eidata`？（Flash 和 RAM 兩份長度一樣，用 `_edata − _sdata` 就算得出來）

#### .text、.rodata、.data、.bss、heap、stack 各放在哪裡？

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

#### 怎麼知道某個全域變數的位址？怎麼算 Flash 和 RAM 用了多少？

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

#### 有初值的全域變數、const、static 區域變數、一般區域變數分別放在哪？

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

#### stack overflow 會發生什麼事？為什麼難除錯？怎麼判斷？

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

#### 加了一個有初值的大陣列後 RAM 快不夠，你怎麼確認它放在哪、佔多少？size 的哪幾欄會變？

**在 .map 找到它在 .data；size 只有 data 欄 +2048，Flash 和 RAM 各多 2048 byte；初值非 0 才會連 Flash 也一起吃**

例子：`uint8_t buffer[2048] = {1};`（全域）

在 `.map` 搜尋 `buffer`，先確認它不在 `Discarded input sections`，再看它在哪個輸出區段：因為有非 0 的初值，會在 `.data` 底下，位址 `0x2000` 開頭，大小 `0x800`。`size` 輸出只有 `data` 欄增加 2048，`text` 和 `bss` 不變。Flash 等於 `text + data`，多 2048；RAM 等於 `data + bss`，也多 2048。重點是：初值只有第一個是 1，其餘 2047 個都是 0，卻還是要在 Flash 存一整份 2048 byte 的初值。如果改成 `= {0}` 或不給初值，它會進 `.bss`，Flash 一個 byte 都不加，只佔 RAM。

| 宣告 | 區段 | `text` | `data` | `bss` | Flash | RAM |
|---|---|---|---|---|---|---|
| `= {1}` | `.data` | — | +2048 | — | +2048 | +2048 |
| `= {0}` 或不給初值 | `.bss` | — | — | +2048 | — | +2048 |
| `const ... = {1}` | `.rodata` | +2048 | — | — | +2048 | — |

可能的追問：如果這個陣列內容永遠不會改呢？（加 `const` → `.rodata`，只佔 Flash，RAM 完全不用）

#### 自己幫新晶片寫 Reset_Handler，要放哪些步驟？清 .bss 和呼叫 main 對調會怎樣？

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

#### 這段程式裡每個變數和函式放在哪裡？

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

#### 設定值莫名變成 0x08001A2F，過一陣子才當機，同事說是指標寫錯，你怎麼看？

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

#### 區域變數宣告 4 KB 陣列，連結成功但執行時按鍵失靈、最後當機，為什麼？怎麼修？

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

#### 面試版說明（出自「SystemInit 執行時，全域變數還不能用」）

- 面試版：「SystemInit 在 C 執行環境準備好之前執行，只能操作暫存器，不能依賴全域變數的初值」

#### 面試版說明（出自「以為 static 區域變數放在 stack」）

- 面試版：「static 區域變數和全域變數放在同一個地方，差別只在誰看得到它的名字」

#### 面試版說明（出自「全域變數變成 0x0800 開頭的奇數：stack overflow 的指紋」）

面試版：「設定值被改成 0x0800 開頭的奇數，我會先懷疑 stack overflow，因為那是 push 到 stack 的返回位址；再用 .list 反查是哪個函式，用 .map 確認變數位置。」

其他提到面試的筆記（全文在這一課的筆記頁）：

- Cortex-M3 暫存器與常見縮寫的全名
- 故意弄壞：無限遞迴造成 stack overflow
- 把 Reset_Handler 裡的動作都當成硬體做的

## 還沒有面試卡的已完成課題

到 App 對這些課題按「複習」，複習結束時 Claude 會把題目整理成面試卡。

- SPRINT-W01-S01 C 語言驗收
- SPRINT-W01-S02 時脈系統（暫存器）
- SPRINT-W01-S03 GPIO（暫存器重做）
- SPRINT-W01-S04 SysTick 與 non-blocking（暫存器）

