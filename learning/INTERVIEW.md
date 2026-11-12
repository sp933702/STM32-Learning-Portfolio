# 面試準備

- 這一頁由學習進度 App 自動彙整，請不要直接修改；要改內容請到 App 改對應的筆記。
- 用法：先遮住答案自己講一次，再對照。講不順的課題回 App 按「複習」再考一次。
- 目前有面試卡 0 則、驗收回答與面試版說明 2 段。

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

#### 面試版說明（出自「BSP_SysTick_GetTick() 與 volatile 的實驗驗證」）

- tick 在 SysTick 中斷加 1、主程式讀；編譯器不知道中斷會改它，可能只讀一次放 CPU 暫存器甚至整段刪除
- 實測 `-O2` 拿掉 `volatile`，延遲迴圈變成跳回自己的無窮迴圈；加回後每圈都有 `ldr` 重讀 SRAM
- `volatile` 不是關掉最佳化，而是禁止省略或快取對該變數的存取
- 限制：`volatile` 不保證原子性；這裡安全是因為 32 bit 讀取一道指令完成，且只有 ISR 寫

其他提到面試的筆記（全文在這一課的筆記頁）：

- 以為 press_event 要加 volatile

## 還沒有面試卡的已完成課題

到 App 對這些課題按「複習」，複習結束時 Claude 會把題目整理成面試卡。

- SPRINT-W01-S01 C 語言驗收
- SPRINT-W01-S02 時脈系統（暫存器）
- SPRINT-W01-S03 GPIO（暫存器重做）

