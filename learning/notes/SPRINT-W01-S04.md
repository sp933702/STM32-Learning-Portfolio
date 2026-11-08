# SPRINT-W01-S04：SysTick 與 non-blocking（暫存器）

- 狀態：**進行中**
- 週次：W01　主題：SysTick
- 對應原任務（HAL 版）：W01-S05, W02-S03
- 進行次數：6 次（最近一次：2026-11-08）
- 程式碼：[projects/SPRINT-W01-S04](../../projects/SPRINT-W01-S04)

## 任務內容

設定 SysTick LOAD/VAL/CTRL 產生 1 ms 中斷，自寫 millis()；重做 non-blocking LED 與按鍵去彈跳狀態機

## 完成標準

tick 計數變數為何要 volatile；32-bit 溢位時 (now - last) 仍正確的原因

## 問題與筆記

### [筆記] 2026-11-04 16:29

【筆記】ST 文件編號：RM、PM、DS、ES、AN
**前綴代表文件類型；ST 周邊查 RM，ARM 核心查 PM**

| 前綴 | 全名 | 內容 | 本板對應 |
|---|---|---|---|
| RM | Reference Manual | ST 周邊暫存器（RCC、GPIO、USART…） | RM0008 |
| PM | Programming Manual | Cortex-M3 核心：指令、NVIC、SysTick、SCB | PM0056 |
| DS | Datasheet | 腳位、電氣規格、封裝 | STM32F103x8 |
| ES | Errata Sheet | 晶片已知 bug 與解法 | 開時脈後讀回延遲 |
| AN | Application Note | 特定主題的實作建議 | |

- SysTick 是 ARM 核心周邊 → 查 PM0056 第 4.5 節，不在 RM0008
- PM0056 名稱 `STK_CTRL`／`STK_LOAD`／`STK_VAL` ＝ CMSIS 的 `SysTick->CTRL`／`LOAD`／`VAL`（CMSIS 由 ARM 定義，各家共用）
- 判斷查哪本：周邊是 ST 加的（GPIO、RCC）→ RM；所有 Cortex-M3 都有的（SysTick、NVIC）→ PM

### [問題] 2026-11-04 16:29 ❓ 未解決

【問題】把 SysTick 的 TICKINT 誤解成「初始化 tick」
**TICKINT 決定數到 0 時要不要產生中斷，跟初始化無關**

| `STK_CTRL` bit | 名稱 | 0 | 1 |
|---|---|---|---|
| 0 | ENABLE | 停止計數 | 開始計數（從 `LOAD` 載入 RELOAD 值往下數） |
| 1 | TICKINT | 數到 0 只設 COUNTFLAG，要輪詢 | 數到 0 觸發 SysTick 中斷 → `SysTick_Handler` |
| 2 | CLKSOURCE | （待查） | （待查） |
| 16 | COUNTFLAG（唯讀） | — | 上次讀取後曾數到 0 |

- 錯在哪：看英文說明時把「SysTick exception request」誤會成初始化
- 正確理解：要每 1 ms 自動讓 tick 加 1，必須讓它產生中斷

### [筆記] 2026-11-04 16:30

【筆記】SysTick 1 ms 中斷：為什麼要做、為什麼排在這裡
**SysTick 是自寫 non-blocking 程式的時間基準，必須在 Clock_Init() 之後、所有 millis() 使用者之前設定**

**為什麼要做**
- 舊 HAL 版的 `HAL_GetTick()` 背後就是 SysTick；不用 HAL 就要自己建時間基準
- 沒有它只能用空迴圈延遲：卡住 CPU、讀不到按鍵，延遲長度還會隨時脈與編譯最佳化改變
- `LOAD` 算錯 → tick 不是 1 ms → LED 週期錯，之後所有 timeout 都跟著錯
- Handler 名字打錯 → 中斷一來就跳進 startup 檔的 `Default_Handler` 無窮迴圈，看起來像當機

**為什麼排在這裡**
- 在 `Clock_Init()` 之後：`LOAD` 依 HCLK 計算；8 MHz 時設定、之後才切到 72 MHz → tick 變成 1/9 ms
- 在所有用到 `millis()` 的程式之前：它們都依賴這個時間基準

### [筆記] 2026-11-04 16:30

【筆記】weak 符號：handler 名字拼錯為什麼不會報錯而是卡死
**startup 檔把每個 handler 宣告成 weak 並指向 Default_Handler；自己寫同名函式才會蓋過去**

```asm
.weak      SysTick_Handler
.thumb_set SysTick_Handler, Default_Handler
```

| 情況 | 連結器用哪份 | 中斷發生時 |
|---|---|---|
| 有寫 `void SysTick_Handler(void)` | 你的（strong 蓋過 weak） | 執行你的程式 |
| 沒寫，或拼錯成 `Systick_Handler` | weak 備用 → `Default_Handler` | 跳進 `b Infinite_Loop`，卡死 |

- 向量表只放「名字」，名字對應到哪個位址由連結器決定
- 拼錯不會有編譯或連結錯誤：拼錯的函式只是一個沒人呼叫的普通函式
- 除錯方法：程式卡住時按 Pause，停在 `Infinite_Loop` → 檢查 handler 名稱

### [筆記] 2026-11-04 16:30

【筆記】SysTick 的時脈來源與 RELOAD = N − 1
**計數器每個時脈減 1，從 RELOAD 數到 0 共 RELOAD + 1 個時脈，所以要 N 個時脈就填 N − 1**

| CLKSOURCE（`SysTick->CTRL` bit 2） | 來源 | 72 MHz 下 |
|---|---|---|
| `0` | AHB / 8 | 9 MHz |
| `1` | 處理器時脈（HCLK） | 72 MHz |

- 數法：RELOAD = 3 → `3 → 2 → 1 → 0 →（重載）3`，一輪 4 個時脈
- 1 ms 需要的時脈數 N = 時脈頻率 × 0.001 s
- RELOAD 欄位 bit 23:0，共 24 bit，最大 `0xFFFFFF`（16,777,215），N − 1 不可超過
- RM0008 時脈樹：HCLK 旁有一條經過 /8 的線通往 Cortex 系統定時器

### [筆記] 2026-11-04 16:31

【筆記】SysTick 的 LOAD 與 VAL：起點與計數器
**LOAD 是每輪的起點（你設定），VAL 是計數器本身（硬體遞減）；只有 VAL 數到 0 才會從 LOAD 重載**

| 暫存器 | 角色 | 誰改 | 讀／寫效果 |
|---|---|---|---|
| `SysTick->LOAD` | 每輪起點，決定一輪多長 | 你，寫一次固定 | 讀寫都是設定值 |
| `SysTick->VAL` | 計數器本身 | 硬體每個時脈減 1 | 讀：目前數到哪；寫任何值：CURRENT 歸 0 並清除 COUNTFLAG |

- 計數器打開後從 `VAL` 目前的值往下數，數到 0 的下一個時脈才載入 `LOAD`，同時（TICKINT = 1 時）觸發中斷
- field ＝ 欄位，這裡指 `VAL` 的 CURRENT（bit 23:0）
- 重設值：PM0056 寫 0，ARMv7-M 架構手冊寫 UNKNOWN；debugger 重新下載不一定斷電 → 不要依賴重設值

### [問題] 2026-11-04 16:31 ❓ 未解決

【問題】SysTick 時脈來源選 72 MHz 的理由講反了
**72 MHz 的優點是解析度高，不是「低速用途也能用」；需要長週期時 /8 反而比較有利**

| | CLKSOURCE = 1（72 MHz） | CLKSOURCE = 0（AHB/8 = 9 MHz） |
|---|---|---|
| 每數一下 | 13.9 ns | 111 ns |
| 24 bit 最長一輪 | ≈ 233 ms | ≈ 1.86 s |
| 1 ms 的 `LOAD` | 71,999 | 8,999 |

- 錯在哪：以為選高速時脈「以後低速也能用」；實際上時脈越快，24 bit 能數的時間越短
- 正確理由：1 ms 兩種都放得下 → 選 72 MHz 換取高解析度（讀 `VAL` 可做微秒級量測），且和 CMSIS／HAL 慣例一致
- 一輪要超過 233 ms 時才需要改用 /8

### [筆記] 2026-11-04 16:32

【筆記】SysTick 設定順序：LOAD → VAL → CTRL
**先把設定準備好，最後才寫 CTRL 打開計數器；VAL 在打開前清 0，第一輪才是完整的 1 ms**

| 順序 | 暫存器 | 做什麼 | 跳過或順序錯會怎樣 |
|---|---|---|---|
| 1 | `SysTick->LOAD` | 設一輪長度 | 先開 `CTRL` → 載入 0 或不確定值，第一輪長度失控 |
| 2 | `SysTick->VAL` | 寫任意值 → 歸 0、清 COUNTFLAG | 殘留舊值（例如 `0xABCD`）→ 第一次中斷提早或延後 |
| 3 | `SysTick->CTRL` | CLKSOURCE、TICKINT、ENABLE 一次設好 | — |

- `LOAD`、`VAL` 都在 `CTRL` 前寫，兩者對調也能動（計數器還沒開）；照 PM0056 4.5.6 與 CMSIS 的順序寫
- RELOAD = 0 時不產生中斷，計數器只會一直重載 0
- 和【筆記】設定順序：先設 ODR，再設 CRL 同一個原則：先設好，最後才打開開關

### [筆記] 2026-11-04 21:03

【筆記】讀取清除的旗標：先拿到值，再清除
**讀 `SysTick->CTRL` 會先回傳當下的 COUNTFLAG，讀完硬體才清 0；看到 1 的那次讀取就是清除它的那次**

```c
while ((SysTick->CTRL & SysTick_CTRL_COUNTFLAG_Msk) == 0U) { }  // 等到數完一輪
```

- `== 0U` 是「繼續等」的條件：讀到 0 → 繼續空轉；讀到 1 → 跳出迴圈 = 數完一輪
- 讀取順序：CPU 拿到當下的值 → 讀完後硬體把 COUNTFLAG 清 0
- 不會漏看：看到 1 的那次讀取同時清掉它；同一個 1 不會被看到兩次
- 比喻：打開信箱看到信就順手拿走，下次要等郵差（下一次數到 0）再送來
- 意義：每次讀到的是「從上次讀到現在，有沒有數完過一輪」

| 時間 | 硬體 | 讀到 | 迴圈 |
|---|---|---|---|
| 0.2 ms | 還在數 | 0 | 繼續等 |
| 1.0 ms | 1 → 0，COUNTFLAG = 1 | — | — |
| 1.0 ms 多一點 | 讀完後清 0 | 1 | 跳出 |

### [問題] 2026-11-04 21:38 ❓ 未解決

【問題】SysTick 的 CMSIS 巨集在 stm32f103xb.h 找不到
**SysTick 是 ARM 核心周邊，定義在 CMSIS 的 core_cm3.h，不是 ST 的裝置標頭檔**

| 定義 | 所在檔案 | 寫的人 |
|---|---|---|
| `GPIOC`、`RCC`、`GPIO_CRH_MODE13_Msk` | `stm32f103xb.h` | ST |
| `SysTick`、`SysTick_Type`、`SysTick_CTRL_ENABLE_Msk` | `core_cm3.h` | ARM（CMSIS） |

- `stm32f103xb.h` 第 131 行 `#include "core_cm3.h"`，所以 include `stm32f1xx.h` 就能用，不必另外 include
- 找法：在 `Inc/CMSIS/core_cm3.h` 搜尋 `SysTick_CTRL_`，命名規則同【筆記】巨集後綴 _Pos、_Msk、_0、_1 的數值
- 判斷原則：周邊屬於 ARM 核心（SysTick、NVIC、SCB）→ `core_cm3.h`；屬於 ST（GPIO、RCC）→ `stm32f103xb.h`

### [問題] 2026-11-04 22:10 ❓ 未解決

【問題】SysTick 的 CMSIS 巨集在 stm32f103xb.h 找不到
**SysTick 是 ARM 核心周邊，定義在 CMSIS 的 core_cm3.h，不是 ST 的裝置標頭檔**

| 定義 | 所在檔案 | 寫的人 |
|---|---|---|
| `GPIOC`、`RCC`、`GPIO_CRH_MODE13_Msk` | `stm32f103xb.h` | ST |
| `SysTick`、`SysTick_Type`、`SysTick_CTRL_ENABLE_Msk` | `core_cm3.h` | ARM（CMSIS） |

- `stm32f103xb.h` 第 131 行 `#include "core_cm3.h"`，所以 include `stm32f1xx.h` 就能用，不必另外 include
- 找法：在 `Inc/CMSIS/core_cm3.h` 搜尋 `SysTick_CTRL_`，命名規則同【筆記】巨集後綴 _Pos、_Msk、_0、_1 的數值
- 判斷原則：周邊屬於 ARM 核心（SysTick、NVIC、SCB）→ `core_cm3.h`；屬於 ST（GPIO、RCC）→ `stm32f103xb.h`

### [問題] 2026-11-04 22:15 ❓ 未解決

【問題】想把 SysTick_Handler 加上 static 來「不公開」
**handler 不能加 static：連結器看不到它，就會改用 weak 的 Default_Handler，中斷一來就卡死**

| 寫法 | 連結器看得到嗎 | 中斷發生時 |
|---|---|---|
| `.c` 裡 `void SysTick_Handler(void)`（不加 static） | 看得到，蓋過 weak | 執行你的程式 |
| `.c` 裡 `static void SysTick_Handler(void)` | 看不到 | 用 weak 備用 → `Default_Handler` 卡死 |

- 「不讓 main 呼叫」靠的是 `.h` 不宣告它，不是加 `static`
- 正確做法：`.h` 不放 handler 宣告；`.c` 照常定義、不加 `static`
- 不報錯、只是卡死，和名字拼錯同一種症狀（見【筆記】weak 符號：handler 名字拼錯為什麼不會報錯而是卡死）

### [筆記] 2026-11-04 22:15

【筆記】handler 就是 ISR，由硬體呼叫
**中斷發生時 CPU 自己查向量表跳進 handler，不是程式呼叫它；所以不放進公開介面**

| 種類 | CMSIS 命名 | 例子 |
|---|---|---|
| 核心系統例外 | `XXX_Handler` | `SysTick_Handler`、`HardFault_Handler` |
| ST 周邊中斷（經 NVIC） | `XXX_IRQHandler` | `EXTI0_IRQHandler`、`USART1_IRQHandler` |

- ISR ＝ Interrupt Service Routine，中斷服務常式
- 名字必須和 startup 檔向量表裡的完全一樣
- main 不會、也不該直接呼叫 handler

### [筆記] 2026-11-04 22:16

【筆記】標頭檔 include 原則：介面要什麼才 include 什麼
**.h 只 include 公開介面需要的；暫存器定義只在 .c 裡 include，而且用 stm32f1xx.h**

| 檔案 | 用到什麼 | 該 include |
|---|---|---|
| `bsp_systick.h` | 只有 `void BSP_SysTick_Init(void);` | 不用 |
| `bsp_systick.c` | `SysTick->...`、`_Msk`、`uint32_t` | `stm32f1xx.h`、`<stdint.h>` |
| `main.c` | 只呼叫 `BSP_...()` | BSP 的 `.h` |

- `.h` include 暫存器定義 → `main.c` 跟著拿到 → `main` 可以直接改暫存器，繞過 BSP（違反【筆記】BSP 介面設計原則）
- `stm32f1xx.h` 是 F1 系列總入口，依專案巨集 `STM32F103xB` 自動選裝置標頭檔；換晶片只改巨集
- 直接 include `stm32f103xb.h` → 程式綁死在這顆晶片
- 介面用到 `uint32_t`（例如 `millis()` 回傳值）時，`.h` 才需要 `<stdint.h>`

### [筆記] 2026-11-04 22:45

【筆記】Debugger 停在 SysTick_Handler 時的 CTRL 與 VAL
**停在 handler 時 CTRL 永遠是 0x10007；VAL 少掉的 18 個時脈就是中斷延遲**

| 觀察 | 值 | 原因 |
|---|---|---|
| `SysTick->LOAD` | 71999（`0x1193F`） | 和預期一致，設定後不變 |
| `SysTick->CTRL`（停在 handler） | `0x10007` | 剛數到 0 → COUNTFLAG = 1；進 handler 不會清，每次 Resume 又被設回 1 |
| `SysTick->CTRL`（在 main 按 Pause） | `0x7` | debugger 讀取已清掉 COUNTFLAG |
| `SysTick->VAL`（停在 `tick++`） | 71981 | 從重載到執行 `tick++` 經過 18 個時脈 |

- CPU 停下來時 SysTick 也停止計數，所以 `VAL` 凍結在 handler 那一刻
- 18 個時脈 ≈ 0.25 µs（72 MHz）＝ 中斷延遲：Cortex-M3 進中斷固定 12 個時脈（硬體推堆疊、查向量表）＋ 函式開頭指令
- 驗證 tick：中斷點停住時 tick 會一次加 1；拿掉中斷點跑一陣子，數值持續增加（實測 4 → 8306）

### [問題] 2026-11-04 22:46 ❓ 未解決

【問題】以為 ~Msk 的值是 0
**~SysTick_VAL_CURRENT_Msk = 0xFF000000，不是 0；~Msk 是遮罩，要和原值做 & 才是「清除欄位」的結果**

| 寫法 | 值／意思 |
|---|---|
| `SysTick_VAL_CURRENT_Msk` | `0x00FFFFFF` |
| `~SysTick_VAL_CURRENT_Msk` | `0xFF000000`（bit 31:24 為 1） |
| `REG & ~Msk` | REG 的這個欄位清 0，其他 bit 保留 |
| `0U` | 0 |

- 錯在哪：把讀改寫 `(REG & ~Msk) \| 新值` 裡的 `~Msk` 當成「清 0 的值」
- 為什麼程式還能動：寫入 `SysTick->VAL` 任何值都會讓 CURRENT 歸 0
- 為什麼要改：bit 31:24 是保留位元，不該寫 1；`~Msk` 讓讀者誤以為在做位元運算
- 正確寫法：`SysTick->VAL = 0U;`

### [筆記] 2026-11-05 11:01

【筆記】SysTick 設定對照 CMSIS SysTick_Config() 與 HAL_InitTick()
**CMSIS 多做了範圍檢查與設最低優先權；HAL 因為切時脈時需要 tick，所以設定兩次**

| 項目 | CMSIS／HAL | 自寫版（修正前） |
|---|---|---|
| `LOAD` 來源 | `SystemCoreClock / 1000` 計算 | 寫死 `71999U` |
| 範圍檢查 | 執行時 `if ((ticks - 1) > 0xFFFFFF) return 1;` | 無 → 改用 `_Static_assert` 編譯時檢查 |
| 優先權 | `NVIC_SetPriority(SysTick_IRQn, 15)` 最低 | 沒設 → 重設值 0（最高） |
| `VAL` | 寫 `0UL` | 寫 `~Msk` → 改為 `0U` |
| 設定次數 | `HAL_Init()`（8 MHz）＋ `HAL_RCC_ClockConfig()` 結尾（72 MHz） | `Clock_Init()` 之後一次 |

- 優先權 0～15，數字越小越優先；F1 用 4 bit，寫在 `SCB->SHP[11]`（SHPR3 bit 31:24）的高 4 bit → 15 寫成 `0xF0`
- 設最低的理由：tick 晚幾微秒無妨，其他中斷（UART、緊急按鍵）不能被它擋
- HAL 讓使用者改 tick 優先權的原因：在中斷裡呼叫 `HAL_Delay()`，若 SysTick 優先權較低就插不進去 → tick 不增加 → 死結；根本解法是不要在中斷裡等待
- HAL 設兩次：`HAL_RCC_OscConfig()` 等 HSE 時用 `HAL_GetTick()` 判斷逾時，所以 8 MHz 時就要有 tick；切到 72 MHz 後 `LOAD` 要重算，否則 tick 快 9 倍
- 自寫版只設一次：`Clock_Init()` 用迴圈次數 `TIME_OUT` 判斷逾時，不需要 tick

### [解法] 2026-11-05 11:02

【解法】SysTick 產生 1 ms 中斷（暫存器版）
**Clock_Init() 之後依序寫 LOAD → 優先權 → VAL → CTRL；LOAD 由 SYSCLK_FREQ_HZ 計算，handler 只做 tick++**

**為什麼**
- 不用 HAL 就沒有 `HAL_GetTick()`，要自己建 1 ms 時間基準，non-blocking 程式全靠它
- `LOAD` 錯 → tick 不是 1 ms；handler 名字錯或加 `static` → 掉進 `Default_Handler` 卡死

**設了什麼、代表什麼**

| 暫存器 | 欄位（bit） | 設定值 | 代表什麼 | 為什麼選這個值 |
|---|---|---|---|---|
| `SysTick->LOAD` | RELOAD（23:0） | `0x1193F`（71999） | 每輪 72,000 個時脈 | 72 MHz × 1 ms，再 −1 |
| `SCB->SHP[11]` | PRI_15（31:24 的高 4 bit） | `0xF0` | SysTick 優先權 15（最低） | tick 晚幾 µs 無妨，讓路給其他中斷 |
| `SysTick->VAL` | CURRENT（23:0） | 寫 `0` | 歸 0、清 COUNTFLAG | 第一輪不受殘留值影響 |
| `SysTick->CTRL` | CLKSOURCE（2） | `1` | 處理器時脈 72 MHz | 解析度高，與 CMSIS／HAL 一致 |
| `SysTick->CTRL` | TICKINT（1） | `1` | 數到 0 觸發中斷 | 每 1 ms 自動進 handler |
| `SysTick->CTRL` | ENABLE（0） | `1` | 開始計數 | 最後才打開 |

- 預期值：`LOAD = 0x0001193F`、`SHP[11] = 0xF0`、`CTRL = 0x7`（停在 handler 時 `0x10007`）
- Debugger 實測：一致

**程式碼**
```c
static volatile uint32_t tick = 0U;

void BSP_SysTick_Init(void)
{
    _Static_assert((SYSCLK_FREQ_HZ / 1000U - 1U) <= SysTick_LOAD_RELOAD_Msk,
                   "SysTick LOAD 超過 24 bit");
    SysTick->LOAD = (SYSCLK_FREQ_HZ / 1000U) - 1U;
    NVIC_SetPriority(SysTick_IRQn, 15U);
    SysTick->VAL  = 0U;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk
                  | SysTick_CTRL_TICKINT_Msk
                  | SysTick_CTRL_ENABLE_Msk;
}

void SysTick_Handler(void)          // 不可加 static，名字要和向量表一致
{
    tick++;
}
```

**為什麼是這個順序**
- 在 `Clock_Init()` 之後：`LOAD` 依 72 MHz 計算
- `LOAD`、優先權、`VAL` 都在 `CTRL` 之前：先設好再打開開關，否則第一輪長度與中斷時間點失控

**對照 CMSIS／HAL**
- `SysTick_Config()` 流程相同（`LOAD` → 優先權 → `VAL` → `CTRL`），範圍檢查在執行時；自寫版用 `_Static_assert` 在編譯時擋
- HAL 設兩次 SysTick（8 MHz、72 MHz），因為切時脈的逾時判斷要用 tick；自寫版 `Clock_Init()` 用迴圈次數逾時，只設一次

### [筆記] 2026-11-05 11:02

【筆記】_Static_assert：編譯時期的檢查
**條件不成立就編譯失敗；只能檢查常數運算式，不產生任何程式碼**

```c
#define SYSTICK_LOAD_VALUE   ((SYSCLK_FREQ_HZ / 1000U) - 1U)

_Static_assert(SYSTICK_LOAD_VALUE <= SysTick_LOAD_RELOAD_Msk,
               "SysTick LOAD 超過 24 bit");
```

| 方式 | 檢查時機 | 失敗時 | 適用 |
|---|---|---|---|
| `_Static_assert` | 編譯時 | 編譯失敗，無法燒錄 | 巨集、數字、`sizeof` 等常數 |
| `if (...) return 錯誤碼;` | 執行時 | 回傳錯誤 | 執行時才知道的值（例如 `SystemCoreClock` 變數） |

- C11 關鍵字，可放在函式外（檔案層級）或函式內
- `LOAD` 完全由巨集決定 → 超過 24 bit 是寫錯，應在編譯時擋下
- HAL 只能用 `if`：它的 `SystemCoreClock` 是變數
- 算式定義成 `.c` 內的巨集，斷言和 `SysTick->LOAD` 共用，避免改了一邊忘了另一邊
- 驗證：暫時把 `1000U` 改成 `1U`（需 72,000,000 > 16,777,215）→ 應出現編譯錯誤

### [筆記] 2026-11-05 21:37

【筆記】GCC 最佳化等級與 CubeIDE 設定位置
**-O0 每次都老實讀寫記憶體；-O2／-Os 會刪掉它認為多餘的讀取，沒加 volatile 的共用變數就會出事**

| 選項 | 意思 | 常見於 |
|---|---|---|
| `-O0` | 不最佳化，逐行翻譯 | Debug 組態預設 |
| `-Og` | 輕度最佳化，方便除錯 | |
| `-O2` | 積極最佳化：搬動、合併、刪除讀寫 | |
| `-Os` | 以大小為優先的最佳化（強度近 `-O2`） | Release 組態常用 |

- 設定位置：專案右鍵 → Properties → C/C++ Build → Settings → Tool Settings → MCU/MPU GCC Compiler → Optimization → Optimization level
- 改完要 Project → Clean 再 Build
- `-O2` 除錯的正常現象：單步跳行、變數 `<optimized out>`、中斷點位置偏移
- 危險之處：`-O0` 下缺 `volatile` 往往看起來正常，換成 Release 才出錯
- 「快取」指放在 CPU 核心暫存器（R0～R12），不是周邊暫存器

### [問題] 2026-11-05 21:38 ❓ 未解決

【問題】延遲函式用 if，沒有等待
**if 只判斷一次就往下走；要「一直等到條件不成立」必須用 while**

```c
// 錯：只檢查一次，立刻返回
if ((tick - start) < ms) { ; }

// 對：重複檢查，直到經過 ms 個 tick
while ((tick - start) < ms) { }
```

- 現象：延遲沒有作用，LED 切換太快，看起來常亮或半亮
- 變數命名：存的是「開始等待的時間點」→ 叫 `start`，不叫 `now`

### [筆記] 2026-11-05 21:39

【筆記】SysTick 延遲的實測與 tick 量化誤差
**邏輯分析儀實測 Delay(500) 為 499.925 ms，誤差來自起點落在某個 tick 中間**

| 量測 | 預期 | 實測 |
|---|---|---|
| 脈寬 | 500 ms | 499.925 ms |
| 週期 | 1000 ms | 999.849 ms（1.00015 Hz） |

- `start = tick` 可能發生在某個 1 ms 的中間 → 第一次 tick 加 1 不到 1 ms → 實際等待介於 499～500 ms
- 量化誤差：以 1 ms 為單位計時，誤差最多 1 個 tick
- 要保證「至少」N ms → 等 N + 1 個 tick（HAL_Delay 的 `wait += 1`）
- 剩餘萬分之一級差異：石英振盪器與邏輯分析儀時脈誤差
- 結論：誤差 0.015%，SysTick 設定正確
- 工具：LA1010（KingstVIS），5 MSa/s 取樣，量測面板直接讀脈寬、週期、頻率

### [問題] 2026-11-05 21:53 ❓ 未解決

【問題】改了最佳化等級，LED 現象卻沒變
**Clean／Build 只在電腦上產生 .elf，沒有按 Debug／Run 下載，晶片跑的還是舊程式**

- 現象：拿掉 `volatile`＋`-O2` 後 LED 照常閃，邏輯分析儀數字和之前幾乎相同
- 查證：`Debug/SPRINT-W01-S04.list` 裡的延遲函式已經變成無窮迴圈，代表新程式碼是對的，只是沒燒進去
- 正確做法：改設定 → Clean → Build → **按 Debug 或 Run 下載** → 才觀察現象

### [筆記] 2026-11-05 21:53

【筆記】拿掉 volatile＋-O2：延遲迴圈被編譯成無窮迴圈
**編譯器認為 tick 在迴圈裡不會變，tick - start 恆為 0，整個迴圈化簡成「跳回自己」，連一次 tick 都不讀**

```c
static uint32_t tick = 0U;           // 沒有 volatile
void BSP_SysTick_Delay(uint32_t ms)
{
    uint32_t start = tick;
    while (tick - start < ms) { }
}
```

```
0800020c <BSP_SysTick_Delay>:
 800020c:  cbnz  r0, 8000210   ; ms != 0 → 跳到 8000210
 800020e:  bx    lr            ; ms == 0 → 返回
 8000210:  b.n   8000210       ; 跳回自己：無窮迴圈
```

- 沒有任何 `ldr` 讀 tick，連 `start = tick` 也被刪掉
- 中斷照常讓 SRAM 裡的 tick 增加，但迴圈根本不看
- `-O0` 下不會發生：每行 C 老實翻譯，每圈都從記憶體讀 tick
- `volatile` 的作用：告訴編譯器這個變數可能被中斷等外部因素改變，每次使用都要重新讀記憶體，不准快取或化簡
- 查反組譯：`Debug/<專案>.list`，或除錯時開 Disassembly 視窗

### [解法] 2026-11-05 22:02

【解法】BSP_SysTick_GetTick() 與 volatile 的實驗驗證
**ISR 寫、主程式讀的 tick 必須 volatile：實測 -O2 拿掉 volatile，延遲迴圈被編譯成無窮迴圈**

**為什麼**
- 編譯器最佳化只分析眼前程式流程，不知道中斷會改 tick
- 少了 `volatile`：`-O0` 正常、`-O2`／`-Os` 卡死 → Debug 正常、Release 才出事

**程式碼**
```c
static volatile uint32_t tick = 0U;     // 只在 .c 內可見，外部透過 GetTick 讀

void SysTick_Handler(void) { tick++; }

uint32_t BSP_SysTick_GetTick(void) { return tick; }
```

**實驗結果**

| `volatile` | 最佳化 | LED | 延遲迴圈反組譯 |
|---|---|---|---|
| 有 | `-O0` | 1 Hz，脈寬 499.92 ms | — |
| 無 | `-O0` | 正常 | — |
| 無 | `-O2` | 卡住；tick 仍在增加 | `b.n 8000210`（跳回自己），無 `ldr` |
| 有 | `-O2` | 正常 | 每圈 `ldr r3, [r2]` 從 `0x2000001c` 讀 tick |

**跨檔案呼叫 GetTick() 為何通常不會卡**
- 編譯器一次只編譯一個 `.c`，看不到函式內容 → 當黑盒子，每圈都呼叫
- 會失效的情況：改成 `.h` 裡的 `static inline`、開 LTO、在同一個 `.c` 內寫等待迴圈
- 結論：正確性不能靠檔案拆分，`volatile` 要標在變數本身

**面試版**
- tick 在 SysTick 中斷加 1、主程式讀；編譯器不知道中斷會改它，可能只讀一次放 CPU 暫存器甚至整段刪除
- 實測 `-O2` 拿掉 `volatile`，延遲迴圈變成跳回自己的無窮迴圈；加回後每圈都有 `ldr` 重讀 SRAM
- `volatile` 不是關掉最佳化，而是禁止省略或快取對該變數的存取
- 限制：`volatile` 不保證原子性；這裡安全是因為 32 bit 讀取一道指令完成，且只有 ISR 寫

### [問題] 2026-11-07 18:03 ❓ 未解決

【問題】把 BSP_GPIO_Led_Toggle() 寫進 bsp_systick 模組
**每個 BSP 模組只管自己的硬體；LED 的操作放 bsp_gpio，bsp_systick 只管時間**

- 錯在哪：Toggle 定義在 `bsp_systick.c`、宣告在 `bsp_systick.h`，並在裡面讀 `GPIOC->IDR`
- 後果：兩個模組都碰 GPIOC；換板子改 LED 腳位時要去改 SysTick 模組，不合理
- 想重用 `BSP_GPIO_Led_On()`／`Off()` → 放進 `bsp_gpio.c` 同檔案直接呼叫即可，不需跨模組
- 判斷原則：問「換硬體時要改哪裡」，答案應該只有一個模組
- 讀 `ODR` 而非 `IDR`：見【解法】LED Toggle 的寫法與風險

### [筆記] 2026-11-07 18:44

【筆記】Toggle 讀 ODR 而不是 IDR
**ODR 是「我命令的輸出」，IDR 是「腳位實際電位」；Toggle 是反轉命令，所以讀 ODR**

| | `ODR` | `IDR` |
|---|---|---|
| 代表 | 命令輸出的值 | 腳位實際電位（取樣） |
| 誰決定 | 程式寫入（BSRR／BRR 改的就是它） | 外部電路＋硬體取樣 |
| 寫完馬上讀 | 立即反映 | 晚幾個時脈 |

- 推挽輸出時兩者通常相同；不同的情況：
  - 開漏輸出：`ODR` = 1 只是放手，外部拉低時 `IDR` = 0 → 用 `IDR` 做 Toggle 會永遠卡住（I²C 就是開漏）
  - 腳位短路或負載過重
  - 剛寫 BSRR 就讀 `IDR`，可能讀到舊值
- 原則：寫的是 `ODR` 就讀 `ODR`；`IDR` 用來確認實際結果（如讀按鍵）

### [筆記] 2026-11-07 18:46

【筆記】週期任務更新時間：last = now 與 last += 週期
**last = now 不會補做但會漂移；last += 週期 長期準時但卡太久會連續補做**

範例：週期 500 ms，t = 1000 那次延遲到 1003 才處理

| 第幾次 | `last = now` | `last += 500U` |
|---|---|---|
| 2 | 1003（last = 1003） | 1003（last = 1000） |
| 3 | 1503 | 1500 |
| 4 | 2003 | 2000 |

卡住 2 秒（t = 1000 → 3000）時，`last += 500U` 會在幾 µs 內連續 toggle 5 次補回進度

| 寫法 | 優點 | 缺點 | 適合 |
|---|---|---|---|
| `last = now` | 不會連續補做 | 延遲累積，週期漂移 | 「間隔至少 N ms」：去彈跳、逾時 |
| `last += 週期` | 長期不漂移 | 卡太久會連續補做 | 取樣、時鐘節拍 |
| `last += 週期`，落後超過一個週期改 `last = now` | 兼顧兩者 | 較複雜 | 一般週期任務 |

- 主迴圈很快時兩者實測無差別；遇到耗時工作（例如畫 SPI 螢幕 10 ms 以上）才會顯現

### [筆記] 2026-11-07 18:47

【筆記】Debugger 看得到其他檔案的 static 變數，卻看不到巨集
**debugger 讀 .elf 的除錯資訊找變數位址，不受 C 的 static 範圍限制；巨集在前處理就消失了**

| | 是什麼 | 在除錯資訊裡 | 停在 `main.c` 時 |
|---|---|---|---|
| `tick`（`bsp_systick.c` 的 static） | 變數，位址 `0x2000001c` | 有 | 看得到 |
| `SysTick`、`GPIOC` | 巨集 | 只在 include 它的檔案範圍 | `Error: Multiple errors reported` |

- `static` 限制的是「程式碼能不能用這個名字」，是給編譯器的規則
- debugger 找名字的順序：區域變數 → 目前檔案 → 整個程式
- 要看暫存器：用 SFRs 視窗，或停在有 include `stm32f1xx.h` 的檔案裡
- 停在 `main.c` 看不到暫存器巨集 = `main.c` 沒 include 暫存器定義，分層乾淨的證據

### [筆記] 2026-11-07 18:48

【筆記】Non-blocking：問一下就走，不在原地等
**時間沒到就立刻離開判斷式去做別的事；主迴圈每圈都很短，多個任務輪流檢查，看起來像同時進行**

```c
uint32_t now = BSP_SysTick_GetTick();
if ((now - led_last_toggle) >= 500U)   // 沒到：馬上往下走
{
    BSP_GPIO_Led_Toggle();
    led_last_toggle = now;
}
background_counter++;                  // 每圈都會執行
```

| | blocking（`Delay(500)`） | non-blocking |
|---|---|---|
| 時間沒到時 | 待在 while 裡等 | 判斷一次就離開 |
| 一圈主迴圈 | 約 500 ms | 不到 1 µs |
| 500 ms 內 `background_counter` 增加 | 1 | 約 81 萬（實測 817,711 → 1,635,424） |

- 比喻：煮飯 20 分鐘，blocking 是盯著電鍋；non-blocking 是做家事時每做完一件瞄一眼時鐘
- 同一個主迴圈可以放多個任務（LED、按鍵、UART），各自記自己的「上次時間」

### [筆記] 2026-11-07 18:48

【筆記】SysTick 實測週期誤差來自頻率比例，不是 tick 量化
**Delay 版與 non-blocking 版都是 499.924 ms／500 ms，固定少約 150 ppm，來自石英與邏輯分析儀時基的誤差**

| 寫法 | 脈寬 | 週期 | 頻率 |
|---|---|---|---|
| `BSP_SysTick_Delay(500)` | 499.925 ms | 999.849 ms | 1.00015 Hz |
| `now - last >= 500` | 499.924 ms | 999.849 ms | 1.00015 Hz |

- 主迴圈很快 → 每次 toggle 緊跟在 tick 加 1 之後，起點都對齊 tick 邊界 → 量化誤差只有 µs 級
- 固定少 76 µs／500 ms ≈ 150 ppm → 頻率比例誤差：板上 8 MHz 石英＋邏輯分析儀時基，兩者誤差加總
- 量化誤差（最多 1 tick）只發生在從任意時間點開始等的時候，例如開機後第一次
- 更正：先前【筆記】SysTick 延遲的實測與 tick 量化誤差把原因歸給量化誤差，是錯的

### [筆記] 2026-11-08 22:23

【筆記】HAL 的 tick 實作對照：uwTick、uwTickFreq、HAL_Delay、__weak
**HAL 的 tick 單位固定是 ms、可降頻省電；HAL_Delay 多等 1 tick 保證至少 N ms；__weak 讓使用者替換時間基準**

| 項目 | HAL | 自寫版 |
|---|---|---|
| 計數變數 | `__IO uint32_t uwTick;`（`__IO` = `volatile`，無 static） | `static volatile uint32_t tick;` |
| 中斷內 | `uwTick += uwTickFreq;` | `tick++;` |
| 中斷頻率 | 可選 1 kHz／100 Hz／10 Hz | 固定 1 kHz |
| 函式 | `__weak`，可被覆蓋 | 一般函式 |

**uwTick 沒有 static 的風險**
- 任何模組都能寫 `uwTick = 0;` → 進行中的逾時計算 `now - start` 變成超大數 → 全部同時逾時
- 自寫版用 `static` 加上只提供 `GetTick()`：外部只能讀

**uwTickFreq**
- Hz = 每秒幾次；1 kHz ↔ 每 1 ms、100 Hz ↔ 每 10 ms
- 值的意義是「每次中斷代表幾 ms」：`1KHZ = 1`、`100HZ = 10`、`10HZ = 100`
- `uwTick += uwTickFreq` → 不論中斷頻率，`uwTick` 單位永遠是 ms
- 降頻目的：省電（睡眠時被叫醒的次數變少），代價是解析度變差

**HAL_Delay 的 `wait += uwTickFreq`**
- 從任意時間點開始等，第一個 tick 可能幾 µs 後就到 → 不加 1 只等 N − 1～N ms
- 加 1 → N～N + 1 ms，保證「至少」N ms（`HAL_Delay(1)` 不加 1 可能只等 1 µs）
- `if (wait < HAL_MAX_DELAY)`：`0xFFFFFFFF` 代表永遠等；再加 1 會溢位成 0，變成完全不等

**__weak 的兩種用途**

| | startup handler | HAL 函式 |
|---|---|---|
| 備用版本 | `Default_Handler` 無窮迴圈 | 完整可用的實作 |
| 目的 | 沒寫就卡住，方便抓錯 | 預設可用，允許替換 |

- 用 RTOS 時 SysTick 被拿去排程 → CubeMX 產生 `stm32f1xx_hal_timebase_tim.c` 重新定義 `HAL_InitTick()`，改用 TIM 當時間基準，HAL 原始碼不用改

### [筆記] 2026-11-08 22:27

【筆記】LOAD 決定中斷頻率；uwTickFreq 讓 tick 單位永遠是 ms
**中斷頻率 = 計數時脈 ÷ (LOAD + 1)；HAL 降頻時每次中斷加「經過的 ms 數」，tick 意義不變**

**LOAD 和 1 kHz 的關係**
- 計數器每秒數 72,000,000 下（72 MHz），一輪數 72,000 下（`LOAD` = 71,999）
- 一秒數完 72,000,000 ÷ 72,000 = 1000 輪 → 一秒中斷 1000 次 = 1 kHz = 每 1 ms 一次
- Hz = 每秒幾次；週期 = 1 ÷ 頻率

| `LOAD` | 一輪多久 | 中斷頻率 |
|---|---|---|
| 71,999 | 1 ms | 1 kHz |
| 719,999（需搭配 /8） | 10 ms | 100 Hz |

**降頻後如果還是 `tick++`**
- 每 10 ms 才加 1 → tick 不再是毫秒 → `now - last >= 500` 變成等 5 秒

**HAL 的解法：`uwTick += uwTickFreq`**

| 中斷頻率 | 每次經過 | `uwTickFreq` | 1 秒後 `uwTick` |
|---|---|---|---|
| 1 kHz | 1 ms | 1 | 1000 |
| 100 Hz | 10 ms | 10 | 1000 |

- `uwTickFreq` 的值是「每次中斷代表幾 ms」，不是 Hz
- 比喻：每 1 ms 拿 1 元或每 10 ms 拿 10 元，一秒後都是 1000 元
- 降頻目的：省電（中斷會把睡眠中的 CPU 叫醒）；代價：解析度變成 10 ms
- 本課固定 1 kHz，`tick++` 即可

### [問題] 2026-11-08 22:30 ❓ 未解決

【問題】Toggle 用了 ODR 的遮罩，卻還在讀 IDR
**同一個 bit 的遮罩在 IDR／ODR 數值相同，編譯器抓不到配對錯誤，只能靠人對照**

```c
if ((GPIOC->IDR & GPIO_ODR_ODR13_Msk) != 0U)   // 錯：暫存器和遮罩不一致
if ((GPIOC->ODR & GPIO_ODR_ODR13_Msk) != 0U)   // 對
```

- `GPIO_ODR_ODR13_Msk` = `GPIO_IDR_IDR13_Msk` = `0x2000` → 程式碼能動，但讀的是腳位電位而非命令
- 巨集名稱中的 `ODR`／`IDR` 就是給人對照的：寫哪個暫存器，就用哪個暫存器的巨集
- 前一版的巨集名 `GPIO_ODR_IDR13_Msk` 不存在 → 不確定名稱時，到 `stm32f103xb.h` 搜尋 `GPIO_ODR_` 找

### [解法] 2026-11-08 22:31

【解法】Non-blocking LED：用 BSP_SysTick_GetTick() 每 500 ms 切換
**每圈讀一次時間，到了才 toggle 並更新上次時間；沒到就離開，主迴圈不被卡住**

**為什麼**
- `Delay()` 等待時 CPU 什麼都不能做；non-blocking 讓 LED、按鍵、UART 能在同一個主迴圈輪流執行
- 這是下一步按鍵去彈跳的基礎：同樣是「每圈看時間，到了才做事」

**程式碼**
```c
// main.c
uint32_t led_last_toggle = BSP_SysTick_GetTick();
for (;;)
{
    uint32_t now = BSP_SysTick_GetTick();
    if ((now - led_last_toggle) >= 500U)
    {
        BSP_GPIO_Led_Toggle();
        led_last_toggle += 500U;     // 不累積延遲；卡太久會連續補做
    }
    background_counter++;
}

// bsp_gpio.c：寫的是 ODR 就讀 ODR
void BSP_GPIO_Led_Toggle(void)
{
    if ((GPIOC->ODR & GPIO_ODR_ODR13_Msk) != 0U)
    {
        BSP_GPIO_Led_On();
    }
    else
    {
        BSP_GPIO_Led_Off();
    }
}
```

**驗證**

| 項目 | 結果 |
|---|---|
| 邏輯分析儀 PC13 | 週期 999.849 ms，脈寬 499.924 ms，1.00015 Hz |
| `background_counter` | 每 500 ms 增加約 81 萬 → 主迴圈未被卡住 |

**為什麼是這個順序**
- `BSP_SysTick_Init()` 在 `BSP_GPIO_Init()` 前後都可以：handler 只碰 tick
- `led_last_toggle` 在進入迴圈前取一次時間，第一次 toggle 才是 500 ms 後

**模組分工**
- Toggle 放 `bsp_gpio`（知道 LED 在 PC13），`bsp_systick` 只管時間
- `main.c` 不 include 任何暫存器定義 → debugger 停在 `main.c` 看不到 `SysTick` 巨集，是分層乾淨的證據

**對照 HAL**

| 自寫版 | HAL | 差異 |
|---|---|---|
| `static volatile uint32_t tick` | `__IO uint32_t uwTick`（無 static） | HAL 任何模組都能改 |
| `tick++` | `uwTick += uwTickFreq` | HAL 可降頻省電，tick 單位仍是 ms |
| 不提供 Delay | `HAL_Delay()` 等 N + 1 tick | 保證至少 N ms；`HAL_MAX_DELAY` 不加 1 避免溢位成 0 |
| 一般函式 | `__weak` | HAL 可被替換成 TIM 時間基準（RTOS 拿走 SysTick 時） |

### [筆記] 2026-11-08 23:05

【筆記】按鍵彈跳實測與去彈跳時間的選擇
**杜邦線碰觸 PB0：按下彈跳在 10 ms 內、放開未觀察到彈跳 → 取 20 ms，有兩倍餘裕且人感覺不到延遲**

- 量法：邏輯分析儀接 PB0，下降沿觸發，取樣率調高後放大看邊緣
- 實測：有時無彈跳，有時多跳幾次，整體都在 10 ms 內；上升沿未見彈跳
- 一般輕觸按鍵：彈跳 1～10 ms，少數到 20 ms；放開也會彈跳，通常較輕微
- 杜邦線額外問題：按住時手抖可能短暫斷開，去彈跳一併擋掉
- 選 20 ms：大於實測最大值的兩倍，又遠低於人感覺「有延遲」的 50～100 ms
