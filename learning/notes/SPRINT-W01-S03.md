# SPRINT-W01-S03：GPIO（暫存器重做）

- 狀態：**進行中**
- 週次：W01　主題：GPIO
- 對應原任務（HAL 版）：W01-S03, W02-S01
- 進行次數：1 次（最近一次：2026-10-20）
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
