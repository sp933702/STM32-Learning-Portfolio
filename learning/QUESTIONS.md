# 問題整理（複習與面試用）

未解決的問題排在最前面。

## ❓ 未解決（24）

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

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-17 18:30）

  【問題】依目前值判斷要不要設定，結果設定被跳過
  **`if ((FLASH->ACR & 0x30U) != 0x30U)` 裡的設定完全沒有執行**
  
  - 復位值 `0x30` 代入：`(0x30 & 0x30) = 0x30` → `0x30 != 0x30` → **不成立**，區塊被跳過
  - 誤會：把「Prefetch 已開啟」當成「Flash 已設定好」
    - 復位值 `0x30` = `0011 0000` → bit 2:0 = `000` → LATENCY 是 **0 WS**，不是 2 WS
  - 後果：LATENCY 維持 0 WS，之後升到 72 MHz 就會讀錯指令 → 程式亂跑或 HardFault
  - 解法：**不要依目前值決定要不要設定，直接設定**（重複寫入同一個值沒有副作用）
  - 注意：括號內運算的值（48）≠ 整個條件的結果（0，不成立）

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-17 18:30）

  【問題】! 和 ~ 搞混，清除欄位時清掉整個暫存器
  **`FLASH->ACR &= (!FLASH_ACR_LATENCY_Msk);` 把整個暫存器清成 0**
  
  | 運算子 | 名稱 | `0x7` 的結果 |
  |---|---|---|
  | `!` | 邏輯 NOT | `0`（結果只有 0 或 1） |
  | `~` | 位元 NOT | `0xFFFFFFF8`（每個 bit 反轉） |
  
  - `&= !Msk` = `&= 0` → **32 個 bit 全部清成 0**，連 PRFTBE 也被關掉
  - 正確清除欄位：`&= ~Msk` → 只清掉遮罩那幾個 bit，其他保持原樣
  - `~0x7UL` 是 32 bit：`0xFFFFFFF8`（不是 `0xFFF8`），少了高位的 1 會誤清 bit 16～31

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-17 22:44）

  【問題】把其他型號才有的周邊列成 C8 的
  **列出的 TIM5～8、USART4～5、ADC3、GPIOF～G，F103C8 其實沒有**
  
  - 原因：看的是 RM0008 的通用時脈圖，涵蓋整個 F10x 系列（含大容量型號）
  - F103C8（中容量）實際的周邊：
  
  | 匯流排 | 周邊 |
  |---|---|
  | APB2（72 MHz） | GPIOA～D、AFIO、ADC1～2、TIM1、SPI1、USART1 |
  | APB1（36 MHz） | TIM2～4、USART2～3、SPI2、I²C1～2、USB、CAN、WWDG、PWR、BKP |
  
  - 原則：
    - **RM0008** 查周邊怎麼運作、暫存器定義（整個系列共用）
    - **Datasheet** 查這顆晶片**實際有哪些**周邊、腳位、頻率上限
  - 面試時說錯自己晶片的周邊，很容易被追問

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-19 22:12）

  【問題】PLLSRC 誤選成 RCC_CFGR_SW_HSE
  **「PLL 輸入選 HSE」誤用 `RCC_CFGR_SW_HSE`**
  
  - 時脈樹上有**兩個**梯形選擇器，用途不同：
  
  | 選擇器 | 位置 | 決定什麼 | 巨集 |
  |---|---|---|---|
  | PLLSRC | PLL **前面** | PLL 的輸入來源 | `RCC_CFGR_PLLSRC_Msk` |
  | SW | SYSCLK **前面** | 系統時脈的來源 | `RCC_CFGR_SW_HSI / HSE / PLL` |
  
  - `RCC_CFGR_SW_HSE` = 把 SYSCLK 直接切到 HSE，跟 PLL 無關
  - 找巨集前先回到時脈樹確認：要設定的是**哪一個**選擇器

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-19 22:12）

  【問題】設定 bit 為 1 誤用 &
  **要把 PLLSRC 設成 1，誤以為要用 `&`**
  
  | 目的 | 寫法 | 效果 |
  |---|---|---|
  | 設成 1 | `REG \|= Msk` | 只有遮罩的 bit 變 1，其他不變 |
  | 清成 0 | `REG &= ~Msk` | 只有遮罩的 bit 變 0，其他不變 |
  | 檢查 | `(REG & Msk) != 0U` | 讀取，不修改暫存器 |
  
  - 錯誤寫法 `REG &= Msk`：**除了遮罩的 bit，其他全部被清成 0**
  - 口訣：`|=` 設定、`&= ~` 清除、`&` 檢查

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-19 22:13）

  【問題】CFGR 預期值算錯：SW/SWS 與 PLLMUL 左移
  **CFGR 預期值算成 `0x003D040A`，正確是 `0x001D0400`**
  
  - 錯誤 1：SW / SWS 填成 `10`（PLL）
    - 步驟 4 **還沒切換**系統時脈，SYSCLK 仍是開機預設的 HSI
    - SW / SWS 對照：`00` = HSI、`01` = HSE、`10` = PLL → 現在應為 `00`
    - `10` 是步驟 5 完成後才會出現的值
  - 錯誤 2：PLLMUL `0111 << 18` 算成 `0x003C0000`
    - `0x3C` = `0011 1100` → 等於 bit 18～21 全為 1（把 `0111` 當成 `1111`）
    - 正確：bit 18、19、20 = 1，bit 21 = 0 → **`0x001C0000`**
  - 換算技巧：先寫出 32 bit 二進位，從右邊每 4 個一組，再逐組換十六進位，不要心算移位

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-19 23:16）

  【問題】迴圈內歸零，timeout 永遠不會觸發
  **`count = 0U;` 寫在 while 迴圈裡，timeout 永遠不會觸發**
  
  - 錯誤寫法：每圈先 `count = 0U` 再 `count++` → 每圈結束 count 都是 1，永遠到不了 5000
  - 後果：等待條件不成立時程式永遠卡死，timeout 形同虛設
  - 解法：
    - `count = 0U;` 放在迴圈**前面**
    - 第二個等待迴圈之前要**重新歸零**（第一個迴圈結束時 count 約 209）
  - 檢查方法：在腦中跑三圈，寫出每圈結束時變數的值

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-19 23:16）

  【問題】等待 PLLRDY 卻讀錯暫存器
  **`while ((RCC->CFGR & RCC_CR_PLLRDY_Msk) == 0U)` 永遠等不到**
  
  - PLLRDY 在 **RCC_CR** 的 bit 25，不是 RCC_CFGR
  - CFGR 的 bit 25 是 **MCO** 欄位的一部分，目前為 0 → 條件永遠成立
  - 加上 ㊲ 的歸零 bug → 程式永遠卡在這個迴圈
  - 巨集名稱已經寫明暫存器：`RCC_CR_PLLRDY_Msk` 要配 `RCC->CR`
  - 習慣：每寫一個位元運算，確認「**哪個暫存器的哪個 bit**」，巨集前綴要跟暫存器一致

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-19 23:16）

  【問題】新增的錯誤碼與既有錯誤碼同值
  **新增 `CLOCK_SWITCH_ERROR 1U`，跟 `CLOCK_ERROR_HSE 1U` 重複**
  
  - 同一個函式回傳 1 時，分不出是 HSE 失敗還是切換失敗
  - `CLOCK_SWITCH_OK` 與 `CLOCK_OK` 重複，成功只需要一個
  - 正確做法：在原本那組錯誤碼後面**接著編號**
  
  | 名稱 | 值 |
  |---|---|
  | `CLOCK_OK` | 0 |
  | `CLOCK_ERROR_HSE` | 1 |
  | `CLOCK_ERROR_PLL` | 2 |
  | `CLOCK_ERROR_SWITCH` | 3 |
  
  - 原則：同一函式的錯誤碼放在同一組、數值不重複

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-19 23:17）

  【問題】等待 SWS 時比較值沒有考慮 bit 位置
  **`while ((RCC->CFGR & RCC_CFGR_SWS_Msk) != 2U)` 切換成功也會 timeout**
  
  - SWS 在 **bit 3:2**，`& Msk` 後數值**仍在原位置、沒有右移**
  - SWS = `10` → `0000 1000` = **`0x8`**，永遠不等於 2
  - 後果：明明切換成功，卻跑到 timeout，回傳「切換失敗」
  - 解法：用巨集比較，位置已算好
    - `while ((RCC->CFGR & RCC_CFGR_SWS_Msk) != RCC_CFGR_SWS_PLL)`
  - 同類錯誤：㉞ 的 PLLMUL 左移；**比較欄位值時一律用巨集，不要自己寫數字**
  - 也不能寫 `== 0U`：SWS 為 `01`（HSE）時同樣不是 0，要比對的是「**等於 PLL**」

- **SPRINT-W01-S02** 時脈系統（暫存器）（2026-10-20 22:48）

  【問題】SW 寫成 RCC->CR：沒切換卻回報成功
  **SW 寫成 `RCC->CR`，`clock_init()` 回傳 `CLOCK_OK`，但 SYSCLK 其實沒切換**
  
  - 錯誤寫法：`RCC->CR = (RCC->CR & ~(SW_Msk | SWS_Msk)) | (SW_PLL | SWS_PLL);`
  - 實際效果（巨集的值被套到 CR）：
    - `& ~0xF` → 清掉 CR 的 bit 0～3（HSION、HSIRDY、保留位、HSITRIM 最低位）
    - `| 0xA` → bit 3 被設成 1 → **改到 HSITRIM**，HSI 頻率偏移
    - SW 完全沒有被設定 → SYSCLK 仍是 HSI 8 MHz
  - 等待迴圈讀 `RCC->CR & 0xC`：剛好讀到被設成 1 的 bit 3 → `0x8` = `RCC_CFGR_SWS_PLL` → **第一圈就判定成功**
  - 這是第二次寫錯暫存器（第一次是 ㊳ 的 PLLRDY）
  - 另一個錯誤：寫入了唯讀的 SWS
  - 防止方法：**巨集前綴必須和暫存器一致**
    - `RCC->CFGR` ↔ `RCC_CFGR_xxx`
    - `RCC->CR` ↔ `RCC_CR_xxx`
    - `FLASH->ACR` ↔ `FLASH_ACR_xxx`


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

- **解法**（2026-10-17 17:36）：

  【解法】為什麼要先調 Flash latency 再升頻（驗收第 2 條）
  **為什麼要先調 Flash latency，再提高 SYSCLK？**
  
  - Flash 讀取需要一段**固定時間**，不會因 CPU 變快而變快
    - 0 WS 最高 24 MHz → Flash 約需 41.7 ns
    - 72 MHz 一個週期 13.9 ns → 41.7 ÷ 13.9 ≈ **3 個週期** → 需額外等 **2 WS**
  - latency 不夠時：CPU 在 Flash 還沒準備好就取指令 → 拿到錯誤指令／資料 → 程式亂跑或 **HardFault**
  - 如果先升頻再設 latency：
    - 中間空檔 CPU 以 72 MHz、0 WS 執行
    - 連「設定 latency 的那條指令」都可能讀錯 → 還沒執行到就當機
  - 先設 latency：此時仍是 8 MHz，多等幾個週期只是稍慢，不會出錯
  - 正確順序：
    - **升頻：先加 latency → 再升頻**
    - **降頻：先降頻 → 再減 latency**
  - 原則：**任何時刻 latency 都要夠用**

- **解法**（2026-10-17 18:31）：

  【解法】Flash latency 的正確寫法與驗證
  **FLASH_ACR 設定：Prefetch 開啟 + 2 WS**
  
  - 開啟 Prefetch：`FLASH->ACR |= FLASH_ACR_PRFTBE_Msk;`
  - 設定 LATENCY（read-modify-write，一行完成）：
    - `FLASH->ACR = (FLASH->ACR & ~FLASH_ACR_LATENCY_Msk) | FLASH_ACR_LATENCY_1;`
  - 通用公式：`REG = (REG & ~欄位Msk) | 新值;`
  - 為什麼不能只用 `|=`：舊值 `001` |= `010` → `011`，舊的 bit 殘留
  - 不要寫 PRFTBS：它是 **r（唯讀）**，硬體回報狀態，寫入無效
  - 驗證：預期 `0011 0010` = **0x32 = 50**，debugger 實際值 50 ✅

- **解法**（2026-10-17 22:43）：

  【解法】APB1 為什麼最高只能 36 MHz（驗收第 3 條）
  **APB1 為什麼最高 36 MHz？**
  
  - 依據：Datasheet 方塊圖標示 APB1 最高 **36 MHz**、APB2 最高 **72 MHz**
  - 原因：晶片設計的取捨
    - **功耗**：動態功耗大致與頻率成正比
    - **時序收斂（Timing closure）**：訊號必須在一個週期內從一個正反器傳到下一個
      - 72 MHz 週期 13.9 ns，36 MHz 週期 27.8 ns
      - 要跑更快需要更快／更大的電晶體 → 面積、功耗、設計與驗證成本都上升
  - ST 的分配：
    - APB2（72 MHz）：需要速度的周邊（GPIO、TIM1、ADC、SPI1、USART1）
    - APB1（36 MHz）：36 MHz 就夠用的周邊（USART2/3、I²C、TIM2～4、USB、CAN）
  - 結論：APB1 電路只依 36 MHz 設計與驗證，超過不在 ST 保證範圍內，屬**硬體規格**
  - 補償機制：APB 分頻 ≠ 1 時，計時器時脈 **×2** → APB1 上的 TIM2～4 仍可拿到 72 MHz

- **解法**（2026-10-19 22:13）：

  【解法】RCC_CFGR 預期值計算表（步驟 4）
  **步驟 4 完成後（尚未切換 SW）的 RCC_CFGR 預期值**
  
  | 欄位 | bit | 設定值 | 左移後 |
  |---|---|---|---|
  | SW | 1:0 | `00` | `0x00000000` |
  | SWS | 3:2 | `00` | `0x00000000` |
  | HPRE | 7:4 | `0000` | `0x00000000` |
  | PPRE1 | 10:8 | `100` | `0x00000400` |
  | PPRE2 | 13:11 | `000` | `0x00000000` |
  | PLLSRC | 16 | `1` | `0x00010000` |
  | PLLXTPRE | 17 | `0` | `0x00000000` |
  | PLLMUL | 21:18 | `0111` | `0x001C0000` |
  | **合計** | | | **`0x001D0400`** |
  
  - 方法：每個欄位單獨算出左移後的值，最後全部 OR 起來
  - 用途：寫程式前先算好，debug 時拿來逐 bit 比對

- **解法**（2026-10-19 23:16）：

  【解法】read-modify-write：設定幾個欄位就清除幾個
  **CFGR 只清除了 PLLXTPRE，其他 5 個欄位沒清**
  
  - 現在剛好能動：開機時這些欄位都是 0
  - 以後會出事：從 Bootloader 跳入、或函式執行第二次時，舊 bit 殘留（同 `001 | 010 = 011`）
  - 正確寫法：
  
  `RCC->CFGR = (RCC->CFGR & ~(RCC_CFGR_PLLSRC_Msk | RCC_CFGR_PLLXTPRE_Msk | RCC_CFGR_PLLMULL_Msk | RCC_CFGR_HPRE_Msk | RCC_CFGR_PPRE1_Msk | RCC_CFGR_PPRE2_Msk)) | (6 個設定值);`
  
  - 原則：**清除的欄位與設定的欄位一一對應**
  - 結構：`REG = (REG & ~(清除清單)) | (設定清單);`，不要混用 `&`、`|` 卻不加括號

- **解法**（2026-10-20 22:50）：

  【解法】上板驗證結果（步驟 5 完成）
  **SYSCLK 72 MHz 上板驗證通過**
  
  | 項目 | 實際值 | 意義 |
  |---|---|---|
  | `clock_state` | 0 | `CLOCK_OK` |
  | `RCC->CFGR` | `0x001D040A` | SW = `10`、SWS = `10` → SYSCLK = PLL ✅ |
  | `RCC->CR` | `0x03038683` | HSE、PLL 皆就緒；HSITRIM = `10000` 未被改動 |
  | `FLASH->ACR` | `0x32` | Prefetch 開啟、2 WS |
  
  - `0xA` = `1010`：bit 1:0（SW）= `10`、bit 3:2（SWS）= `10`
  - 切換 SW 後第一次檢查 SWS 就已完成（count = 0）
  - 中斷點在 `main()` 時，`clock_init()` 內的區域變數會顯示 Error，屬正常


