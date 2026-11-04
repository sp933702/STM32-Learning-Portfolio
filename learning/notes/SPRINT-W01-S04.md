# SPRINT-W01-S04：SysTick 與 non-blocking（暫存器）

- 狀態：**進行中**
- 週次：W01　主題：SysTick
- 對應原任務（HAL 版）：W01-S05, W02-S03
- 進行次數：1 次（最近一次：2026-11-03）

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
