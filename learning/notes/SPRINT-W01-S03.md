# SPRINT-W01-S03：GPIO（暫存器重做）

- 狀態：**進行中**
- 週次：W01　主題：GPIO
- 對應原任務（HAL 版）：W01-S03, W02-S01
- 進行次數：5 次（最近一次：2026-10-27）
- 程式碼：[projects/SPRINT-W01-S03](../../projects/SPRINT-W01-S03)

## 任務內容

建立不使用 HAL 的專案；手動開 RCC_APB2ENR，設定 CRH/CRL（PC13 推挽輸出、PB0 上拉輸入），用 BSRR/BRR 控 LED、IDR 讀按鍵

## 完成標準

能說明 F1 的 CNF/MODE 4-bit 編碼；為何 BSRR 比讀改寫 ODR 安全；上拉輸入為何要寫 ODR=1

## 問題與筆記

### [筆記] 2026-10-21 21:42

【筆記】CMSIS 總入口與晶片巨集
**程式一律 include `stm32f1xx.h`，由巨集決定載入哪顆晶片的標頭檔**

| 項目 | 內容 |
|---|---|
| `stm32f1xx.h` | F1 系列總入口，本身不定義暫存器 |
| `-DSTM32F103xB` | 專案 Preprocessor 設定，讓總入口載入 `stm32f103xb.h` |
| `stm32f103xb.h` | 真正的暫存器定義（基底位址、結構、bit 遮罩） |

- 不要直接 include `stm32f103xb.h`：等於繞過選型號的機制，換晶片要逐檔修改
- 追定義來源：對 `#include` 或暫存器名稱按 **F3**（Open Declaration）
- 料號解碼（Datasheet → Ordering information scheme）

| 片段 | 意義 |
|---|---|
| F103 | performance line |
| C | 48 pin |
| 8 | Flash 64 KB（B = 128 KB）→ Medium-density |
| T | LQFP 封裝 |
| 6 | -40～85°C |

### [筆記] 2026-10-21 21:42

【筆記】.h／.c 拆分原則
**.h 放「呼叫者需要知道的」，.c 放「實作細節」**

| 放在 .h | 放在 .c |
|---|---|
| 函式宣告 `uint32_t Clock_Init(void);` | 函式實作 |
| 呼叫者要用的常數（`CLOCK_OK`、`CLOCK_ERROR_xxx`） | 內部常數（`TIME_OUT`） |
| 介面需要的型別標頭 `<stdint.h>` | 暫存器標頭 `stm32f1xx.h` |
| — | 只在檔案內用的輔助函式（加 `static`） |

- **Include guard**：`#ifndef CLOCK_INIT_H／#define／#endif`，防止重複引入（面試常問）
- **Self-contained**：標頭檔用到什麼型別，就自己 include 對應標頭，不依賴別人先 include
- **.c 第一行先 include 自己的 .h**：若 .h 不是 self-contained，編譯時會馬上報錯
- 暫存器標頭放 .c 不放 .h：使用者只需要知道函式介面，不用看到暫存器（隱藏實作）
- 資料夾分工：自己的檔案放 `Inc/`、`Src/`；廠商檔案放 `Inc/CMSIS/`，不要混放

### [問題] 2026-10-21 21:42 ❓ 未解決

【問題】main.c 出現 'CLOCK_OK' undeclared
**錯誤碼定義在 clock_init.c，main.c 看不到**

- 原因：`#define` 只在定義它的檔案內有效，`main.c` 只 include 了 `clock_init.h`
- 解法：呼叫者會用到的常數（錯誤碼）搬到 `clock_init.h`
- 判斷原則：問自己「呼叫這個函式的人需要知道它嗎？」需要 → .h；不需要 → .c

### [問題] 2026-10-21 21:43 ❓ 未解決

【問題】Build 成功，但編輯器顯示 Unresolved inclusion: "clock_init.h"
**真正原因：新程式存到了 S02 專案的 main.c**

| 專案 | 當時的 main.c | 結果 |
|---|---|---|
| S02 | 新版（include `clock_init.h`） | S02 沒有 `clock_init.h` → Unresolved inclusion |
| S03 | 舊版（時鐘程式還寫在 main.c） | Build 通過，但其實沒用到 `clock_init.c` |

- 檢查：看視窗**標題列**路徑，例如 `workspace - SPRINT-W01-S03/Src/main.c`
- 預防：不用的專案右鍵 → **Close Project**；開檔一律從 Project Explorer 對應專案展開
- 還原：S02 已 commit，用 Git 取回 HEAD 版本
- 和 S02 那則「Index → Rebuild」不同：那次是索引沒更新，這次是真的改錯檔案

### [解法] 2026-10-21 21:43

【解法】複製舊專案建立新課題專案
**Copy → Paste 之後要處理名稱與 launch 設定兩個坑**

1. Project Explorer 對舊專案右鍵 → Copy → Paste，取新名稱
2. 刪掉新專案的 `Debug/` 資料夾
3. 名稱檢查：顯示成 `名稱 (in 資料夾)` 代表專案名稱 ≠ 資料夾名稱 → 右鍵 **Rename** 改成一致
4. 刪掉複製過來的 `舊專案 Debug.launch`（它仍指向舊專案的 `.elf`）
5. 右鍵 → **Debug As → STM32 C/C++ Application**，自動產生新的 launch 設定
6. 路徑和名稱不要有空白，避免 GCC／Make 出錯

- 自我檢查：燒錄後故意改一個明顯行為，板子沒變 → 先懷疑 launch 設定
- Workspace 不用切換：同一個 Workspace 可以放多個專案

### [筆記] 2026-10-21 22:15

【筆記】RM0008 中文版與英文版節號對照
**中文版章節編號比英文版少 1，討論與面試以英文版為準**

| 暫存器 | 中文版 | 英文版（Rev 17） |
|---|---|---|
| RCC_APB2RSTR | 6.3.4 | 7.3.4 |
| RCC_APB2ENR | 6.3.7 | 7.3.7 |
| GPIOx_CRL | 8.2.1 | 9.2.1 |
| GPIOx_BSRR | 8.2.5 | 9.2.5 |
| GPIOx_BRR | 8.2.6 | 9.2.6 |

- 原因：英文版多了一章，RCC 在英文版是第 7 章，中文版是第 6 章
- 英文版第 8 章是互聯型（F105/107）的 RCC，F103 不要看那一章
- 中文翻譯版較舊，內容有疑問時以英文版為準
- 檔案位置：`Desktop\STM32 參考文件\`

### [筆記] 2026-10-21 22:15

【筆記】RCC_APB2ENR：開啟 GPIO 時脈
**F1 的周邊開機時預設沒有時脈，沒開時脈的話，寫 GPIO 暫存器完全無效**

| 項目 | 內容 |
|---|---|
| 節號 | 中文版 6.3.7／英文版 7.3.7 |
| 位址偏移 | 0x18（RCC 基底 0x4002_1000 + 0x18） |
| 復位值 | 0x0000_0000（全部周邊時脈關閉） |
| bit 2 | IOPAEN：GPIOA |
| bit 3 | IOPBEN：GPIOB（本課按鍵 PB0） |
| bit 4 | IOPCEN：GPIOC（本課 LED PC13） |

- 名稱意義：IOP = I/O Port，EN = Enable
- 寫法：`RCC->APB2ENR |= (RCC_APB2ENR_IOPBEN_Msk | RCC_APB2ENR_IOPCEN_Msk);`
- 用 `|=` 不用 `=`：APB2ENR 同時管 AFIO、USART1、SPI1、ADC1 等周邊的時脈
  - 用 `=` 開 USART1 時，會把 GPIO 的時脈一起關掉，這種 bug 很難找
  - 和 S02 的原則相同：只動自己的欄位
- 預期結果：bit 3、bit 4 為 1 → `0x0000_0018`

### [問題] 2026-10-21 22:15 ❓ 未解決

【問題】開 GPIO 時脈時誤用 APB2RSTR 的 mask
**ENR = 時脈致能；RSTR = 周邊重置，兩者 bit 位置相同但意義完全不同**

| 暫存器 | 節號（中／英） | offset | 寫 1 的意義 |
|---|---|---|---|
| RCC_APB2RSTR | 6.3.4／7.3.4 | 0x0C | 周邊維持在重置狀態，直到軟體寫 0 |
| RCC_APB2ENR | 6.3.7／7.3.7 | 0x18 | 開啟周邊時脈 |

- 我的錯誤：寫成 `RCC_APB2RSTR_IOPBRST_Msk`，第二次又寫成 `RCC_APB3ENR_IOPAEN`
- 正確：`RCC_APB2ENR_IOPBEN_Msk`（bit 3）、`RCC_APB2ENR_IOPCEN_Msk`（bit 4）
- 命名規則：周邊_暫存器_bit名稱_Msk，前半段要和寫入的暫存器一致
- F1 只有 APB1、APB2，沒有 APB3；IOPB 是 port B，IOPA 是 port A
- 數值相同還是要用對名稱：程式碼是寫給人讀的，看到 RSTR 會誤以為在重置周邊
- 如果真的 `|=` 到 RCC->APB2RSTR：重置的是 **port B**（不是 A），而且會一直卡在重置狀態，GPIOB 的設定全部無效，PB0 永遠讀不到
- RSTR 正確用法：先寫 1 再寫 0，讓周邊回到復位值（驅動程式重新初始化時使用）
- 驗證名稱：打錯會出現 undeclared；也可以按 F3 跳進 `stm32f103xb.h` 確認

### [筆記] 2026-10-21 22:46

【筆記】多行巨集為什麼要用 do { } while(0)
**讓巨集變成「一個敘述」，在 if／else 中才不會出錯（面試常考）**

只用大括號：`#define LED_ON() { a(); b(); }`

```c
if (x)
    { a(); b(); };   // 結尾的 ; 是另一個空敘述，if 到此結束
else                 // error: 'else' without a previous 'if'
```

改用 do-while：`#define LED_ON() do { a(); b(); } while (0)`

```c
if (x)
    do { a(); b(); } while (0);   // ; 屬於 do-while 語法，整體是一個敘述
else
    ...
```

- `while(0)` 條件不成立，內容剛好執行一次，目的不是迴圈
- 附帶好處：忘記加分號會編譯錯誤，強迫像函式一樣使用

### [解法] 2026-10-21 22:48

【筆記】HAL 開時脈巨集 __HAL_RCC_GPIOC_CLK_ENABLE() 拆解
**設好 bit 後讀回一次，用讀取動作當作延遲**

```c
#define __HAL_RCC_GPIOC_CLK_ENABLE()   do { \
        __IO uint32_t tmpreg; \
        SET_BIT(RCC->APB2ENR, RCC_APB2ENR_IOPCEN); \
        /* Delay after an RCC peripheral clock enabling */ \
        tmpreg = READ_BIT(RCC->APB2ENR, RCC_APB2ENR_IOPCEN); \
        UNUSED(tmpreg); \
    } while(0U)
```

| 程式 | 作用 |
|---|---|
| `SET_BIT(REG, BIT)` | 開時脈，展開後就是「REG 或等於 BIT」 |
| `tmpreg = READ_BIT(...)` | 讀回同一暫存器：CPU 必須等前一筆寫入完成才能讀，形成延遲 |
| `__IO uint32_t tmpreg` | `__IO` = `volatile`，防止編譯器把沒人用的讀取刪掉 |
| `UNUSED(tmpreg)` | `(void)tmpreg`，消除 set but not used 的 warning |
| `do { } while(0U)` | 把多行巨集包成「一個敘述」 |

- 為什麼要延遲：開時脈的寫入經過匯流排要幾個週期才生效，馬上設定周邊可能被忽略
- 讀回的「值」不重要，「讀」這個動作才重要（不是二次確認）
- 正式記載於 ST Errata Sheet（Delay after an RCC peripheral clock enabling）
- 自己的寫法：`(void)RCC->APB2ENR;`（Step 5 決定是否加入 bsp_gpio.c）
- 定義位置：`SET_BIT`、`READ_BIT` 在 `stm32f1xx.h`；`__IO` 在 `core_cm3.h`；`UNUSED` 是 HAL 專用（`stm32f1xx_hal_def.h`）
- volatile 的「暫存器」要分清楚：CPU 暫存器（R0～R12）vs 周邊暫存器（RCC->APB2ENR）

### [解法] 2026-10-21 22:48

【解法】單一 bit 與多 bit 欄位的寫法選擇
**單一 bit 不需要先清再設**

| 欄位類型 | 寫法 | 例子 |
|---|---|---|
| 單一 bit 設 1 | 或等於 | 開 GPIOB、GPIOC 時脈 |
| 單一 bit 清 0 | 且等於「反相 mask」 | 關閉某個 bit |
| 多 bit 欄位 | 先清再設 | S02 的 PLLMUL（4 bit） |

```c
// 單一 bit 設 1
RCC->APB2ENR |= (RCC_APB2ENR_IOPBEN_Msk | RCC_APB2ENR_IOPCEN_Msk);

// 單一 bit 清 0
REG &= ~BIT_Msk;

// 多 bit 欄位：先清再設
REG = (REG & ~FIELD_Msk) | FIELD_VALUE;
```

- 我原本的寫法：單一 bit 也先清再設 → 結果相同，但清除那一步沒有作用
- `a = a | b` 縮寫成 `a |= b`：暫存器名稱只寫一次，避免左右寫成不同暫存器
- 同一行的 mask 名稱要統一（都用 `_Msk`）
- 驗證：APB2ENR 前 `0x0` → 後 `0x18`（`0b11000`，bit 3、bit 4 = 1）

### [筆記] 2026-10-22 21:59

【筆記】F1 GPIO 的 CNF/MODE 4-bit 編碼
**每個腳位用 4 bit 設定：高 2 bit 是 CNF，低 2 bit 是 MODE**

| 暫存器 | 節號（中／英） | offset | 復位值 | 管哪些腳位 |
|---|---|---|---|---|
| GPIOx_CRL | 8.2.1／9.2.1 | 0x00 | 0x4444_4444 | pin 0～7 |
| GPIOx_CRH | 8.2.2／9.2.2 | 0x04 | 0x4444_4444 | pin 8～15 |

- L／H = Low／High，指「低編號 8 隻腳／高編號 8 隻腳」，跟速度無關
- 32 bit ÷ 4 bit = 8 個腳位，所以 16 隻腳要兩個暫存器
- 欄位名稱的數字 = 腳位編號（MODE13、CNF13 = pin 13）；暫存器是 GPIOA～E 共用格式
- 起始 bit：CRL 為 y × 4，CRH 為 (y − 8) × 4 → PC13 在 CRH 的 bit [23:20]

**MODE（低 2 bit）：決定輸入或輸出，輸出時決定最大速度（表18）**

| MODE | 意義 |
|---|---|
| 00 | 輸入模式（復位值） |
| 01 | 輸出，最大 10 MHz |
| 10 | 輸出，最大 2 MHz |
| 11 | 輸出，最大 50 MHz |

**CNF（高 2 bit）：意義依 MODE 而不同（表17）**

| CNF | 輸入模式（MODE = 00） | 輸出模式（MODE 不為 00） |
|---|---|---|
| 00 | 類比輸入 | 通用推挽 |
| 01 | 浮空輸入（復位值） | 通用開漏 |
| 10 | 上拉／下拉輸入 | 複用推挽 |
| 11 | 保留 | 複用開漏 |

**常用組合**

| 用途 | CNF | MODE | 4-bit |
|---|---|---|---|
| 復位值：浮空輸入 | 01 | 00 | 0100 = 0x4 |
| PC13 通用推挽輸出 2 MHz | 00 | 10 | 0010 = 0x2 |
| PB0 上拉輸入（Step 4） | 10 | 00 | 1000 = 0x8 |

- 復位值 0x4444_4444 = 每個腳位都是 0100 → 開機全部是浮空輸入

### [筆記] 2026-10-22 22:01

【筆記】GPIO 模式名詞：推挽／開漏、通用／複用、浮空／上拉／下拉／類比
**一個腳位的設定要回答三件事：方向、誰在控制、電路結構**

**輸出電路結構**：腳位內部有兩個開關，上開關（P-MOS）接 VDD、下開關（N-MOS）接 GND

| 模式 | 輸出 1 | 輸出 0 | 用途 |
|---|---|---|---|
| 推挽 Push-Pull | 上開關導通，推到 VDD | 下開關導通，拉到 GND | LED、一般數位輸出 |
| 開漏 Open-Drain | 放開（懸空），靠外部上拉電阻拉高 | 下開關導通，拉到 GND | I²C、多裝置共用線、不同電壓介面 |

**誰在控制腳位**

| 模式 | 腳位聽誰的 | 例子 |
|---|---|---|
| 通用 General Purpose | 程式（ODR、BSRR） | 點 LED |
| 複用 Alternate Function | 晶片內的周邊硬體 | USART TX、PWM 輸出、SPI SCK |

- 複用模式下寫 ODR 無效（表17 的 PxODR 欄寫「不使用」）

**輸入電路結構**

| 模式 | 腳位內部 | 沒接東西時讀到 |
|---|---|---|
| 浮空 Floating | 什麼都不接，像天線 | 不確定，受雜訊亂跳 |
| 上拉 Pull-up | 內部電阻接 VDD | 1 |
| 下拉 Pull-down | 內部電阻接 GND | 0 |
| 類比 Analog | 關閉數位電路，接到 ADC | ADC 使用 |
                VDD
                 │
               [上開關]  ← P-MOS
                 │
  腳位 ──┤
                 │
               [下開關]  ← N-MOS
                 │
                GND
- 開機預設浮空輸入：腳位不輸出電壓，不會和外部電路衝突，最安全
- 按鍵 PB0 按下接 GND → 要用上拉，放開時才會穩定讀到 1

### [問題] 2026-10-22 22:03 ❓ 未解決

【問題】GPIO 設定的兩個誤解
**L／H 不是速度；LED 一設成輸出就會亮**

| 誤解 | 正確 |
|---|---|
| CRL 的 L 代表低速，PC13 不需要高速所以用 CRL | L／H 代表 pin 0～7／pin 8～15；PC13 是 pin 13 → CRH；速度由 MODE 決定 |
| PC13 設成輸出後 LED 是暗的 | ODR 復位值 0 → 輸出 0 → Active-Low LED 亮 |

- 找不到「PC13」：暫存器圖是 GPIOx 共用格式，要看欄位名稱的數字（MODE13、CNF13）
- 預測腳位行為時，要同時考慮「設定（CRH）」和「資料（ODR）」兩個暫存器

### [筆記] 2026-10-22 22:04

【筆記】ODR 與 PC13 LED 電路
**輸出模式下，腳位電位 = ODR 對應 bit 的值；PC13 LED 是 Active-Low**

| 項目 | 內容 |
|---|---|
| ODR | Output Data Register，bit y 對應 pin y，只用 bit 15:0 |
| ODR 復位值 | 0 → PC13 一設成輸出就輸出 0 |
| LED 電路 | 3.3V → 電阻 → LED → PC13 |
| Active-Low | PC13 輸出 0（接地）才有電流 → 亮；輸出 1 → 暗 |
| LED 位置 | 板上標示 PC13 的那顆（另一顆是電源燈） |

- 驗證：CRH 設定完成（0x44244444）的瞬間 LED 就亮了，因為 ODR bit13 = 0
- PC13～PC15 驅動能力弱：速度不超過 2 MHz、不能當電流源 → 板子只能接成 Active-Low

**推挽 vs 開漏（用 PC13 LED 推導）**

| 輸出值 | 推挽 | 開漏 |
|---|---|---|
| 0 | 接 GND → 亮 | 接 GND → 亮 |
| 1 | 接 3.3V → 暗 | 懸空，沒有電流路徑 → 暗 |

- 這個電路兩種都能用：LED 接在 3.3V，等於幫腳位提供上拉
- LED 改成 Active-High（PC13 → LED → GND）時，開漏無法輸出高電位 → 不能用
- 選推挽：兩個方向都主動驅動，最通用；開漏用於 I²C 共用線、不同電壓的介面
- 輸出懸空 = 沒有電流路徑（結果確定）；輸入懸空 = 讀值不確定（兩者不同）

### [解法] 2026-10-22 22:05

【解法】PC13 設為通用推挽輸出 2 MHz
**CNF13 + MODE13 是多 bit 欄位 → 先清再設**

```c
// PC13：CNF13 = 00（通用推挽）、MODE13 = 10（輸出 2 MHz）
GPIOC->CRH = (GPIOC->CRH & ~(GPIO_CRH_MODE13_Msk | GPIO_CRH_CNF13_Msk))
           | GPIO_CRH_MODE13_1;
```

- 清除：兩個欄位都要清（共 4 bit），設定幾個欄位就清幾個
- 設定：只需設 MODE13 的 bit 1（GPIO_CRH_MODE13_1 = bit 21），CNF13 = 00 清完就是了
- 可用巨集：在 stm32f103xb.h 搜尋 GPIO_CRH_MODE13
- 預測值：0x4444_4444 只改 bit [23:20]，0100 → 0010 → 0x4424_4444
- 驗證：Debugger 讀到 GPIOC->CRH = 0x44244444，與預測一致；LED 同時亮起

### [筆記] 2026-10-22 22:52

【筆記】GPIO 資料暫存器：IDR／ODR／BSRR／BRR
**ODR 儲存輸出值；BSRR、BRR 是「命令」暫存器，只寫不存**

| 暫存器 | 節號（中／英） | offset | 復位值 | 屬性 | 作用 |
|---|---|---|---|---|---|
| GPIOx_IDR | 8.2.3／9.2.3 | 0x08 | 0x0000_XXXX | r | 讀取腳位實際電位 |
| GPIOx_ODR | 8.2.4／9.2.4 | 0x0C | 0x0000_0000 | rw | 輸出資料，bit y = pin y |
| GPIOx_BSRR | 8.2.5／9.2.5 | 0x10 | 0x0000_0000 | w | 設定或清除 ODR 的指定 bit |
| GPIOx_BRR | 8.2.6／9.2.6 | 0x14 | 0x0000_0000 | w | 清除 ODR 的指定 bit |

**BSRR 的兩半**

| 位置 | 名稱 | 寫 1 | 寫 0 |
|---|---|---|---|
| bit 15:0 | BSy（Bit Set） | ODR bit y 設為 1 | 沒有效果 |
| bit 31:16 | BRy（Bit Reset） | ODR bit y 清為 0 | 沒有效果 |

- BRy 位置公式：bit (y + 16)，例如 BR13 = bit 29
- BRR 只有 BRy（bit 15:0），功能等同 BSRR 的 bit 31:16；BRR 只能清除，不能設定
- IDR 的 X：沒有固定值，反映腳位實際電位，所以唯讀
- BSRR、BRR 是寫入專用，讀回來固定是 0（不儲存值）
  - 寫法用 `=` 不用 `|=`：寫 0 的 bit 沒效果，直接寫入也不會影響其他腳位
- 與 CRL／CRH 合起來，GPIO 暫存器 offset 依序為：CRL 0x00、CRH 0x04、IDR 0x08、ODR 0x0C、BSRR 0x10、BRR 0x14
補充：寫入專用的暫存器讀回來是什麼

BSRR、BRR 都是寫入專用（屬性標 w），讀回來固定是 0。原因是它們不儲存任何值：

ODR 是「儲存」暫存器：寫進去的值會被記住，讀回來就是那個值。
BSRR 是「命令」暫存器：寫入的瞬間，硬體依照你寫的 1 去設定或清除 ODR，動作完成後什麼都不留。

### [解法] 2026-10-22 22:52

【解法】用 BSRR／BRR 控制 PC13 LED（Active-Low）
**LED 亮 = PC13 輸出 0 = 清除 bit 13**

| 動作 | ODR bit 13 | BSRR 寫哪個 bit | BRR 寫哪個 bit |
|---|---|---|---|
| LED 亮 | 0 | bit 29（BR13） | bit 13 |
| LED 暗 | 1 | bit 13（BS13） | 做不到，BRR 只能清除 |

- Active-Low：先想「腳位要輸出 0 還是 1」，再決定用 Set 還是 Reset
- 名稱別寫錯：BSRR（Bit Set／Reset Register）、BRR（Bit Reset Register），沒有 BSR

### [問題] 2026-10-22 22:52 ❓ 未解決

【問題】LED 亮／暗用錯 Set／Reset
**直覺以為「亮 = Set（寫 1）」，但 PC13 LED 是 Active-Low**

- 錯誤答案：亮 → BS13；暗 → BS13（還把 BSRR 打成 BSR）
- 正確答案：亮 → 清除 bit 13（BSRR bit 29 或 BRR bit 13）；暗 → 設定 bit 13（BSRR bit 13）
- 原因：電路是 3.3V → LED → PC13，腳位接地（0）才有電流
- 預防：寫程式前先畫出電路，確認有效電位（Active-High 或 Active-Low）
- 後續做法：在 bsp_gpio 裡包成 LED_On()／LED_Off()，把 Active-Low 的細節藏在函式裡，上層不用記

### [筆記] 2026-10-24 21:54

【筆記】為什麼 BSRR 比讀改寫 ODR 安全
**讀改寫 ODR 不是原子操作，中斷會讓副本過時；BSRR 一次寫入、只影響指定腳位**

讀改寫寫法：`GPIOC->ODR &= ~(1U << 13);` 會被拆成「讀出 → 修改 → 寫回」

情境：主程式要清 PC13；ISR 要設 PC14；一開始 ODR = 0x2000

| 時間 | 誰在執行 | 動作 | 主程式的副本 | 實際 ODR |
|---|---|---|---|---|
| t1 | 主程式 | 讀出 ODR | 0x2000 | 0x2000 |
| t2 | 主程式 | 清除 bit 13 | 0x0000 | 0x2000 |
| t3 | ISR | 設定 bit 14 | 0x0000（不變） | 0x6000 |
| t4 | 主程式 | 寫回副本 | 0x0000 | 0x0000 ← PC14 被蓋掉 |

- 問題根源：三個步驟可被中斷，副本在中斷後已過時
- 「寫回前再讀一次」解決不了：重新讀之後還要改、寫，一樣可能被打斷

BSRR 寫法：`GPIOC->BSRR = GPIO_BSRR_BR13_Msk;`

- 原因 1：只有一次寫入，沒有讀出步驟 → 原子操作，不會被打斷
- 原因 2：寫 0 的 bit 沒效果 → 只影響 PC13，PC14 等其他腳位維持原樣
- 注意：`=` 寫進 BSRR，不是把 ODR 整個換掉；硬體只處理寫 1 的 bit

### [解法] 2026-10-24 21:54

【解法】用 BSRR／BRR 控制 PC13 LED 的實作與驗證
**命令暫存器用 = 直接寫入**

```c
GPIOC->BSRR = GPIO_BSRR_BS13_Msk;   // PC13 = 1 → 暗
GPIOC->BSRR = GPIO_BSRR_BR13_Msk;   // PC13 = 0 → 亮
GPIOC->BSRR = GPIO_BSRR_BS13_Msk;   // 暗
GPIOC->BRR  = GPIO_BRR_BR13_Msk;    // 亮（BRR 只能清除）
```

| 步驟 | 寫入 | ODR | LED |
|---|---|---|---|
| ① | BSRR BS13 | 0x2000 | 暗 |
| ② | BSRR BR13 | 0x0000 | 亮 |
| ③ | BSRR BS13 | 0x2000 | 暗 |
| ④ | BRR BR13 | 0x0000 | 亮 |

- 第一次寫成 `|=`：結果一樣，但 BSRR 讀回恆為 0，多讀一次沒有意義
- Debugger 觀察 BSRR 恆為 0，證實寫入專用暫存器不儲存值
- 8192 = 0x2000 = 只有 bit 13 為 1

### [筆記] 2026-10-24 22:24

【筆記】上拉輸入為什麼要寫 ODR = 1
**CNF = 10 只代表「上拉或下拉」，由 ODR 的 bit 決定是哪一個**

| 模式 | CNF | MODE | 4-bit | PxODR |
|---|---|---|---|---|
| 上拉輸入 | 10 | 00 | 1000 | 1 |
| 下拉輸入 | 10 | 00 | 1000 | 0 |

- 輸出模式：ODR bit = 腳位輸出的電位
- 輸入模式（CNF = 10）：ODR bit = 選擇上拉（1）或下拉（0）
- PxODR 的 x 是 port 字母（PBODR = GPIOB 的 ODR），不是腳位編號
- 設定方式：`GPIOB->BSRR = GPIO_BSRR_BS0_Msk;`（用 BSRR，不必讀改寫 ODR）

**電路（按鍵接 PB0 與 GND）**

| 按鍵狀態 | PB0 接到 | IDR bit 0 |
|---|---|---|
| 放開 | 經上拉電阻（約 40 kΩ）接 VDD | 1 |
| 按下 | 經按鍵直接接 GND | 0 |

- 按下時讀到 0 → 按鍵也是 Active-Low
- 電阻的作用：決定放開時的電位，並在按下時限制電流（否則 VDD 直接短路到 GND）

**忘記寫 ODR = 1 的後果**

- ODR 復位值是 0 → 變成下拉輸入
- 放開讀到 0、按下也讀到 0 → 按鍵完全沒有作用
- 程式和 CRL 看起來都正確，很難發現

### [筆記] 2026-10-24 22:25

【筆記】上拉輸入為什麼要寫 ODR = 1
**CNF = 10 只代表「上拉或下拉」，由 ODR 的 bit 決定接通哪一顆內部電阻**

| 模式 | CNF | MODE | 4-bit | PxODR |
|---|---|---|---|---|
| 上拉輸入 | 10 | 00 | 1000 | 1 |
| 下拉輸入 | 10 | 00 | 1000 | 0 |

**晶片內部結構**

```
  VDD ──[上拉電阻]──/ ──┐   ← ODR = 1 時接通
                        ├── PB0
  GND ──[下拉電阻]──/ ──┘   ← ODR = 0 時接通
```

| 模式 | 接通的電阻 | 沒有外力時的電位 |
|---|---|---|
| 上拉輸入 | 上拉電阻接 VDD | 1 |
| 下拉輸入 | 下拉電阻接 GND | 0 |
| 浮空輸入（CNF = 01） | 兩顆都不接 | 不確定 |

- 輸出模式：ODR bit = 腳位輸出的電位
- 輸入模式（CNF = 10）：ODR bit = 選擇上拉（1）或下拉（0）
- PxODR 的 x 是 port 字母（PBODR = GPIOB 的 ODR），不是腳位編號
- 設定方式：`GPIOB->BSRR = GPIO_BSRR_BS0_Msk;`（用 BSRR，不必讀改寫 ODR）

**按鍵電路（按鍵接在 PB0 與 GND 之間）**

| 按鍵狀態 | PB0 接到 | IDR bit 0 |
|---|---|---|
| 放開 | 經上拉電阻（約 40 kΩ）接 VDD | 1 |
| 按下 | 經按鍵直接接 GND | 0 |

- 按下時讀到 0 → 按鍵也是 Active-Low
- 電阻的作用：決定放開時的電位；按下時限制電流（否則 VDD 直接短路到 GND）

**忘記寫 ODR = 1 的後果**

- ODR 復位值是 0 → 變成下拉輸入
- 放開讀到 0、按下也讀到 0 → 按鍵完全沒有作用
- 程式和 CRL 看起來都正確，很難發現

### [問題] 2026-10-27 22:54 ❓ 未解決

【問題】讀按鍵時沒有 mask，LED 恆暗
**IDR 包含整個 port 16 隻腳的電位，只判斷一個腳位時必須先 & mask**

- 錯誤寫法：`if (GPIOB->IDR != 0U)`
- 正確寫法：`if ((GPIOB->IDR & GPIO_IDR_IDR0_Msk) != 0U)`
- 現象：不論按下或放開，LED 都是暗的
- Debugger 讀到 `GPIOB->IDR` = 0xFFF3、0xFFF1：bit 0 都是 1（兩次都是放開）；差在 bit 1，PB1 浮空輸入讀值亂跳
- 原因：其他腳位不一定是 0（浮空亂跳、JTAG 腳位預設帶上拉），整個 IDR 永遠不等於 0
- PB2 = BOOT1，板上接 GND，所以 bit 2 恆為 0

**判斷單一 bit：一律和 0U 比較**

| 運算 | 結果 |
|---|---|
| `IDR & GPIO_IDR_IDR0_Msk` | 0 或 0x0001 |
| `IDR & GPIO_IDR_IDR13_Msk` | 0 或 0x2000（不是 1） |

- `&` 之後 bit 留在原位置，不會移到 bit 0
- 寫 `== 1U` 只對 pin 0 有效，換腳位就錯 → 用 `== 0U` 或 `!= 0U`

### [解法] 2026-10-27 22:54

【解法】PB0 上拉輸入讀按鍵、控制 PC13 LED
**先設 ODR（選上拉），再設 CRL（切成輸入上拉／下拉）**

```c
// PB0 上拉輸入：先設 ODR 再設 CRL
GPIOB->BSRR = GPIO_BSRR_BS0_Msk;
GPIOB->CRL  = (GPIOB->CRL & ~(GPIO_CRL_CNF0_Msk | GPIO_CRL_MODE0_Msk))
            | GPIO_CRL_CNF0_1;               // CNF0 = 10、MODE0 = 00

for (;;)
{
    if ((GPIOB->IDR & GPIO_IDR_IDR0_Msk) != 0U)
    {
        GPIOC->BSRR = GPIO_BSRR_BS13_Msk;    // 放開：PC13 = 1 → LED 暗
    }
    else
    {
        GPIOC->BSRR = GPIO_BSRR_BR13_Msk;    // 按下：PC13 = 0 → LED 亮
    }
}
```

| 項目 | 預測 | 實測 |
|---|---|---|
| GPIOB->CRL | 0x4444_4448 | 一致 |
| GPIOB->ODR | 0x0000_0001 | 一致 |
| 按下（PB0 接 GND） | LED 亮 | LED 亮 |
| 放開 | LED 暗 | LED 暗 |

- 沒有按鍵：用杜邦線一端接 GND、另一端碰 PB0 代替；內部上拉約 40 kΩ，電流約 0.08 mA，安全
- 杜邦線只能碰 PB0，不要碰 3.3V／5V（會短路）
- 第一次寫成 `ODR |=`：改成 BSRR，程式裡不再出現 ODR 的讀改寫

### [筆記] 2026-10-27 22:54

【筆記】設定順序：先設 ODR，再設 CRL
**先設資料、再切模式，避免腳位出現短暫的錯誤狀態**

| 順序 | 中間狀態 | 結果 |
|---|---|---|
| 先 CRL 後 ODR | CNF = 10 但 ODR = 0 → 短暫下拉輸入 | 讀到 0，誤判為按下 |
| 先 ODR 後 CRL | 仍是浮空輸入，內部電阻都沒接上 | ODR 沒有作用，也沒有副作用 |

- 本課影響很小（只有幾個時脈週期），但接了外部電路的腳位可能出問題（例如馬達、電源控制）
- 輸出腳也適用：先用 BSRR 設好初始電位，再把 CRH／CRL 切成輸出，避免輸出瞬間的錯誤電位
