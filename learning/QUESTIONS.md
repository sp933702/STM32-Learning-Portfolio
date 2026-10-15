# 問題整理（複習與面試用）

未解決的問題排在最前面。

## ❓ 未解決（13）

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 10:51）

  【卡關】RM0008是甚麼? 我要如何取得?

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 13:23）

  標題： RM0008 是什麼？要查哪份文件？
  
  解法：
  1. RM0008：ST 官方的 F101/102/103/105/107 參考手冊，查周邊功能與暫存器的 bit 定義。
  2. Datasheet：查腳位、電氣特性、Flash 大小與頻率上限。
  3. PM0056：查 Cortex-M3 核心，例如 NVIC、SysTick、HardFault。
  建議用英文版，中文翻譯版較舊，章節編號可能不同。

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 13:24）

  標題： STM32F103C8 屬於哪種容量等級？
  
  解法：
  
  型號最後的 8 代表 Flash 為 64 KB，屬於 Medium-density（中容量）。
  
  容量等級：小容量 16～32 KB、中容量 64～128 KB、大容量 256～512 KB。
  
  F101/102/103 共用同一張時脈樹圖；F105/107（互聯型）的圖不同。

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 15:01）

  【問題】為什麼開啟 HSE 後一定要等 HSERDY？
  - 石英剛通電要一段時間才會穩定振盪，頻率和波形都不穩
  - 沒等就切過去：時脈不對，周邊頻率錯，嚴重時 MCU 直接當機

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 15:01）

  【解法】石英壞了，等待迴圈會卡死
  - `while ((RCC->CR & RCC_CR_HSERDY) == 0);` 若 HSERDY 永遠是 0 → 無窮迴圈，程式卡死，後面都不會執行
  - 解法：加 **timeout** 計數器，輪詢 N 次還沒就緒就跳出
  - 跳出後**不能**繼續設 PLL，要回傳錯誤（之後 W03 會做統一錯誤碼）

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 15:02）

  【問題】F103C8 要定義哪個巨集？
  - `STM32F103xB`：中容量系列（C8 64 KB、CB 128 KB）共用同一個
  - 設定位置：Project → Properties → C/C++ Build → Settings → MCU GCC Compiler → Preprocessor
  - 定義後 `stm32f1xx.h` 才會載入對應的 `stm32f103xb.h`

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 21:15）

  【問題】CubeIDE 2.x 找不到 New → STM32 Project
  
  - 原因：CubeIDE 2.0 起把 CubeMX 從 IDE 拆出去，舊入口被移除（網路教學多半是舊版畫面）
  - 解法：**File → STM32 Project Create/Import** → 選 **Empty Project**
  - 選項：語言 **C**、Binary Type **Executable**

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 21:18）

  【問題】建立專案出現 Project location is not empty repository
  **建立專案時出現「Project location is not empty repository」，Next 無法按**
  
  - 原因：取消勾選 Use default location 後，Location 要填**專案本身的資料夾**，我填成上一層 `projects\`，裡面已有 `SPRINT-W01-S01`
  - 解法：路徑後面補上專案名稱
    - 錯：`...\STM32-Learning-Portfolio\projects\`
    - 對：`...\STM32-Learning-Portfolio\projects\SPRINT-W01-S02`
  - 資料夾不存在也沒關係，CubeIDE 會自動建立

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 21:20）

  【問題】Build 成功，但狀態列顯示 Unresolved inclusion
  **Build 0 errors，但狀態列顯示 `Unresolved inclusion: <stm32f1xx>`**
  
  - 原因：不是編譯錯誤，是 CubeIDE 的程式碼索引（Indexer）還沒更新
  - 影響：編輯器出現波浪線、自動完成可能失效
  - 解法：專案右鍵 → **Index → Rebuild**
  - 寫法慣例：
    - 自己專案的標頭檔用雙引號 `#include "stm32f1xx.h"`
    - 系統／編譯器內建的用角括號 `#include <stdint.h>`

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 21:21）

  【問題】手冊 HSEON 是 bit 16，標頭檔卻寫 bit 0？
  
  - 原因：看錯成 `HSION`，兩者只差一個字母
  
  | 名稱 | 意思 | 位置 |
  |---|---|---|
  | HS**I**ON | Internal 內部 8 MHz RC | bit 0 |
  | HS**E**ON | External 外部石英 | bit 16 |
  
  - 驗證：搜尋 `RCC_CR_HSEON_Pos` → `16U`
  - 拿手冊和標頭檔互相核對是好習慣（IC bring-up 常要抓兩者不一致）

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 22:04）

  【問題】位元運算沒加括號，等待迴圈一次都不執行
  **`while(RCC->CR >> RCC_CR_HSERDY_Pos & 1U != 1U)` 迴圈一次都不執行**
  
  - 可以編譯、不會報錯，但石英壞了也會回傳「成功」（最危險的錯誤）
  - 原因：運算子優先順序
  
  | 優先順序 | 運算子 |
  |---|---|
  | 高 | `>>` 移位 |
  | 中 | `!=` 相等比較 |
  | 低 | `&` 位元 AND |
  
  - 編譯器實際理解成：`(CR >> Pos) & (1U != 1U)` → `x & 0` → 永遠是 0
  - 口訣：`&`、`|`、`^` 的優先順序比 `==`、`!=` **低**（C 語言公認的設計缺陷）

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 22:05）

  【問題】MCU 上 printf 的輸出去哪了？
  **在 MCU 上呼叫 printf，字會印到哪裡？**
  
  - MCU 沒有螢幕或終端機，`printf` 最後呼叫 `syscalls.c` 的 `_write()`
  - `_write()` 再交給 `__io_putchar()`，預設沒有接到任何硬體 → 看不到輸出
  - 要真的印到電腦：把 `__io_putchar` / `_write` 接到 UART（W02 USART 會做）
  - 其他問題：
    - 會連結大量 C 函式庫程式碼，程式變大
    - 沒有 `\n` 時內容常卡在緩衝區，不會立即送出
  - 目前做法：用 debugger 看變數與暫存器（中斷點 + Variables + SFRs）

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-15 22:11）

  【問題】ST-LINK 顯示 No device found on target
  **Debug 失敗：`Error in initializing ST-LINK device. Reason: No device found on target.`**
  
  - 意思：電腦找得到 ST-LINK，但 ST-LINK 透過 SWD 找不到 MCU
  - STM32CubeProgrammer 也連不上 → 問題在**硬體連線**，不是程式或專案設定
  - 本次原因：**麵包板接觸不良**，改用雙母杜邦線直接連接就成功
  - 麵包板簧片會氧化、鬆脫，SWD 這類高速訊號特別容易受影響
  - 燒錄／debug 失敗時，第一步先排除麵包板


## ✅ 已解決的問題與解法

### [SPRINT-W01-S01](notes/SPRINT-W01-S01.md) C 語言驗收

- **問題**（2026-10-15 09:54）：

  預測題判斷錯了 long long，理由寫成「匯流排寬度」

- **解法**（2026-10-15 09:54）：

  韌體程式一律使用 <stdint.h> 的固定寬度型別


### [SPRINT-W01-S02](notes/SPRINT-W01-S02.md) 時脈系統（暫存器）

- **解法**（2026-10-15 13:25）：

  標題： 72 MHz 的時脈設定推導
  內容：
  
  HSE 8 MHz → PLLXTPRE 選 ÷1 → PLLMUL ×9 → 72 MHz。
  不選 ÷2，因為 8 ÷ 2 = 4，需要 ×18，超過 PLLMUL 上限 ×16。
  AHB ÷1 = 72 MHz、APB2 ÷1 = 72 MHz。
  APB1 ÷2 = 36 MHz，因為上限是 36。
  只用 HSI 時：8 ÷ 2 × 16 = 64 MHz，到不了 72，所以必須啟用 HSE。

- **解法**（2026-10-15 21:19）：

  【解法】建立純暫存器專案的完整步驟
  **CubeIDE 2.x 建立純暫存器（不用 HAL）專案**
  
  1. File → STM32 Project Create/Import → Empty Project，晶片選 `STM32F103C8Tx`
  2. 在專案 `Inc\` 底下新增 `CMSIS\` 資料夾
  3. 從 `STM32Cube\Repository\STM32Cube_FW_F1_V1.8.7\` 複製標頭檔：
     - `Drivers\CMSIS\Device\ST\STM32F1xx\Include\` → `stm32f1xx.h`、`stm32f103xb.h`、`system_stm32f1xx.h`
     - `Drivers\CMSIS\Include\` → 全部 `.h`（`core_cm3.h` 會再引用其他檔）
  4. 專案右鍵 → Refresh（F5）
  5. Properties → C/C++ Build → Settings → MCU GCC Compiler
     - Preprocessor：加 `STM32F103xB`
     - Include paths：加 `../Inc/CMSIS`
  6. `main.c` 加 `#include "stm32f1xx.h"` → Build → **0 errors**

- **解法**（2026-10-15 22:04）：

  【解法】等待旗標 + timeout 的標準寫法
  **等待 HSERDY 的正確寫法（含 timeout）**
  
  - 推薦：直接用遮罩判斷，不移位
    - `while ((RCC->CR & RCC_CR_HSERDY_Msk) == 0U)`
  - 若要移位，一律加括號：`(((RCC->CR >> Pos) & 1U) != 1U)`
  - 迴圈內計數，超過 `TIME_OUT` 就 `return` 失敗，避免石英故障時卡死
  - `TIME_OUT` 用 `#define TIME_OUT 5000U` 定義，數值之後依實測與 datasheet 調整
  - 函式無參數要寫 `(void)`，空括號 `()` 在 C 代表「參數不確定」


