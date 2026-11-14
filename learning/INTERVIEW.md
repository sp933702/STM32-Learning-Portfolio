# 面試準備

- 這一頁由學習進度 App 自動彙整，請不要直接修改；要改內容請到 App 改對應的筆記。
- 用法：先遮住答案自己講一次，再對照。講不順的課題回 App 按「複習」再考一次。
- 目前有面試卡 0 則、驗收回答與面試版說明 4 段。

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

## 還沒有面試卡的已完成課題

到 App 對這些課題按「複習」，複習結束時 Claude 會把題目整理成面試卡。

- SPRINT-W01-S01 C 語言驗收
- SPRINT-W01-S02 時脈系統（暫存器）
- SPRINT-W01-S03 GPIO（暫存器重做）
- SPRINT-W01-S04 SysTick 與 non-blocking（暫存器）
- SPRINT-W01-S05 Startup 與 Linker Script

