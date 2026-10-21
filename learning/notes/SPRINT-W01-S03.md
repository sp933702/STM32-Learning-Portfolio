# SPRINT-W01-S03：GPIO（暫存器重做）

- 狀態：**進行中**
- 週次：W01　主題：GPIO
- 對應原任務（HAL 版）：W01-S03, W02-S01
- 進行次數：2 次（最近一次：2026-10-21）
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
