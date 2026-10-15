# SPRINT-W01-S02：時脈系統（暫存器）

- 狀態：**進行中**
- 週次：W01　主題：RCC
- 對應原任務（HAL 版）：W03-S01
- 進行次數：3 次（最近一次：2026-10-15）
- 程式碼：[projects/SPRINT-W01-S02](../../projects/SPRINT-W01-S02)

## 任務內容

讀 RM0008 RCC 章節；只用 CMSIS 標頭檔 stm32f1xx.h，手動啟用 HSE、設 Flash latency 2WS、PLL×9 → SYSCLK 72 MHz、APB1 ÷2

## 完成標準

用 debugger 確認 RCC->CFGR 的 SWS 已切到 PLL；能解釋為何先調 Flash latency、APB1 為何最高 36 MHz

## 問題與筆記

### [問題] 2026-10-15 10:51 ❓ 未解決

【卡關】RM0008是甚麼? 我要如何取得?

### [問題] 2026-10-15 13:23 ❓ 未解決

標題： RM0008 是什麼？要查哪份文件？

解法：
1. RM0008：ST 官方的 F101/102/103/105/107 參考手冊，查周邊功能與暫存器的 bit 定義。
2. Datasheet：查腳位、電氣特性、Flash 大小與頻率上限。
3. PM0056：查 Cortex-M3 核心，例如 NVIC、SysTick、HardFault。
建議用英文版，中文翻譯版較舊，章節編號可能不同。

### [問題] 2026-10-15 13:24 ❓ 未解決

標題： STM32F103C8 屬於哪種容量等級？

解法：

型號最後的 8 代表 Flash 為 64 KB，屬於 Medium-density（中容量）。

容量等級：小容量 16～32 KB、中容量 64～128 KB、大容量 256～512 KB。

F101/102/103 共用同一張時脈樹圖；F105/107（互聯型）的圖不同。

### [筆記] 2026-10-15 13:24

標題： 怎麼看時脈樹圖
內容：

四種元件：
振盪器（OSC／RC）：時脈來源
梯形選擇器（MUX）：從多個輸入選一個，旁邊會標控制位元名稱，例如 SW、PLLSRC
分頻器（/N、Prescaler）
倍頻器（PLLMUL）
看法：從目的地沿著線往回追。
手冊上標的是可選範圍，例如 HSE 4–16 MHz、PLLMUL ×2～×16；自己畫圖時要寫實際設定值。

### [筆記] 2026-10-15 13:25

標題： F103 時脈來源與匯流排上限
內容：

時脈來源：
HSI RC 8 MHz：內部
HSE OSC 4–16 MHz：外部石英，本板為 8 MHz
LSE 32.768 kHz：RTC 用
LSI 40 kHz：IWDG 用
匯流排上限：SYSCLK 72、HCLK 72、PCLK1 36、PCLK2 72（單位 MHz）
USB 需要 48 MHz：72 ÷ 1.5 = 48

### [解法] 2026-10-15 13:25

標題： 72 MHz 的時脈設定推導
內容：

HSE 8 MHz → PLLXTPRE 選 ÷1 → PLLMUL ×9 → 72 MHz。
不選 ÷2，因為 8 ÷ 2 = 4，需要 ×18，超過 PLLMUL 上限 ×16。
AHB ÷1 = 72 MHz、APB2 ÷1 = 72 MHz。
APB1 ÷2 = 36 MHz，因為上限是 36。
只用 HSI 時：8 ÷ 2 × 16 = 64 MHz，到不了 72，所以必須啟用 HSE。

### [筆記] 2026-10-15 15:00

【筆記】怎麼看 RM0008 暫存器圖
| 位置 | 內容 | 怎麼用 |
|---|---|---|
| 標題下方 | 偏移地址、復位值 | 復位值 = 開機時的預設值 |
| 格子圖 | 上排 bit 31~16、下排 bit 15~0 | 從格子上方數字看出是第幾位 |
| 格子下方小字 | rw / r / res | rw 可讀寫、r 只能讀、res 保留不要動 |
| 最下方文字 | 每個 bit 的 0/1 意義 | 真正的意義看這裡 |

- 讀的順序：格子圖找名稱 → 看 bit 編號 → 到文字說明找同名條目
- 命名規律：結尾 **ON** 通常是開關（rw）、結尾 **RDY** 通常是就緒旗標（r，硬體自己設）
- 中文版頁碼和英文版不同，討論時用**節號**

### [筆記] 2026-10-15 15:00

【筆記】RCC_CR 的 HSE 相關 bit

| bit | 名稱 | 屬性 | 意義 |
|---|---|---|---|
| 16 | HSEON | rw | 1 = 開啟 HSE |
| 17 | HSERDY | r | 1 = HSE 已穩定就緒（硬體設定） |
| 18 | HSEBYP | rw | 1 = 旁路，直接吃外部時脈訊號 |

- HSEBYP：跳過內部振盪電路，給「主動式振盪器／外部時脈訊號」用
- 本板接**被動石英**，需要內部電路起振 → HSEBYP 設 **0**
- HSEBYP 只能在 HSE **關閉**時修改

### [問題] 2026-10-15 15:01 ❓ 未解決

【問題】為什麼開啟 HSE 後一定要等 HSERDY？
- 石英剛通電要一段時間才會穩定振盪，頻率和波形都不穩
- 沒等就切過去：時脈不對，周邊頻率錯，嚴重時 MCU 直接當機

### [問題] 2026-10-15 15:01 ❓ 未解決

【解法】石英壞了，等待迴圈會卡死
- `while ((RCC->CR & RCC_CR_HSERDY) == 0);` 若 HSERDY 永遠是 0 → 無窮迴圈，程式卡死，後面都不會執行
- 解法：加 **timeout** 計數器，輪詢 N 次還沒就緒就跳出
- 跳出後**不能**繼續設 PLL，要回傳錯誤（之後 W03 會做統一錯誤碼）

### [問題] 2026-10-15 15:02 ❓ 未解決

【問題】F103C8 要定義哪個巨集？
- `STM32F103xB`：中容量系列（C8 64 KB、CB 128 KB）共用同一個
- 設定位置：Project → Properties → C/C++ Build → Settings → MCU GCC Compiler → Preprocessor
- 定義後 `stm32f1xx.h` 才會載入對應的 `stm32f103xb.h`

### [問題] 2026-10-15 21:15 ❓ 未解決

【問題】CubeIDE 2.x 找不到 New → STM32 Project

- 原因：CubeIDE 2.0 起把 CubeMX 從 IDE 拆出去，舊入口被移除（網路教學多半是舊版畫面）
- 解法：**File → STM32 Project Create/Import** → 選 **Empty Project**
- 選項：語言 **C**、Binary Type **Executable**

### [問題] 2026-10-15 21:18 ❓ 未解決

【問題】建立專案出現 Project location is not empty repository
**建立專案時出現「Project location is not empty repository」，Next 無法按**

- 原因：取消勾選 Use default location 後，Location 要填**專案本身的資料夾**，我填成上一層 `projects\`，裡面已有 `SPRINT-W01-S01`
- 解法：路徑後面補上專案名稱
  - 錯：`...\STM32-Learning-Portfolio\projects\`
  - 對：`...\STM32-Learning-Portfolio\projects\SPRINT-W01-S02`
- 資料夾不存在也沒關係，CubeIDE 會自動建立

### [筆記] 2026-10-15 21:18

【筆記】Project Explorer 移除舊專案（不刪檔案）
**從 workspace 移除舊專案，但保留檔案**

- Project Explorer 顯示的是 workspace 裡登記過的專案，不代表都在同一個資料夾
- 右鍵 → **Delete** → **不要勾** Delete project contents on disk → OK
  - ⚠️ 勾了會連檔案一起刪除，且不進資源回收筒
- 只想收起來：右鍵 → **Close Project**
- 要加回來：File → Open Projects from File System

### [解法] 2026-10-15 21:19

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

### [筆記] 2026-10-15 21:19

【筆記】CMSIS 標頭檔是什麼、為什麼要複製
**CMSIS 標頭檔 = C 語言版的 Register Map**

| 檔案 | 內容 |
|---|---|
| `stm32f1xx.h` | 總入口，依巨集選擇要載入哪顆晶片的標頭檔 |
| `stm32f103xb.h` | 周邊基底位址、暫存器結構、每個 bit 的遮罩 |
| `core_cm3.h` | Cortex-M3 核心：NVIC、SysTick |

- 沒有它：`*(volatile uint32_t *)0x40021000 |= (1 << 16);`
- 有了它：`RCC->CR |= RCC_CR_HSEON;`（兩行做的事完全相同）
- 複製進專案的好處：
  - Git 同步到另一台電腦可直接編譯
  - 版本固定，不受韌體包更新影響
  - 檔案就在專案裡，方便查暫存器定義
- 放在 `Inc` 只是慣例（Inc 放 .h、Src 放 .c），編譯器只看 Include paths
- 另開 `CMSIS` 子資料夾：區分廠商程式與自己的程式

### [筆記] 2026-10-15 21:20

【筆記】Include paths 與 Preprocessor 設定的意義
**MCU GCC Compiler 設定 = 編譯指令的參數**

- 編譯第一階段是**前處理器**：先處理 `#include`、`#define`、`#if`，再真正編譯

| 設定 | 變成參數 | 作用 |
|---|---|---|
| Include paths `../Inc/CMSIS` | `-I../Inc/CMSIS` | 告訴編譯器去哪找 .h，沒設會出現 No such file or directory |
| Preprocessor `STM32F103xB` | `-DSTM32F103xB` | 等於每個 .c 最上面都加 `#define STM32F103xB` |

- 為什麼不在 main.c 寫 `#define`：之後有多個 .c 檔，專案設定定義一次才會一致
- 路徑用 `../`：編譯是在 `Debug\` 資料夾執行，`..` 回到專案根目錄
- 驗證：Build 後在 Console 找 `arm-none-eabi-gcc ... main.c` 那行，可看到 `-D`、`-I`
- 若巨集沒定義：`stm32f1xx.h` 的 `#if/#elif` 全部不成立 → `#error` 編譯失敗

### [問題] 2026-10-15 21:20 ❓ 未解決

【問題】Build 成功，但狀態列顯示 Unresolved inclusion
**Build 0 errors，但狀態列顯示 `Unresolved inclusion: <stm32f1xx>`**

- 原因：不是編譯錯誤，是 CubeIDE 的程式碼索引（Indexer）還沒更新
- 影響：編輯器出現波浪線、自動完成可能失效
- 解法：專案右鍵 → **Index → Rebuild**
- 寫法慣例：
  - 自己專案的標頭檔用雙引號 `#include "stm32f1xx.h"`
  - 系統／編譯器內建的用角括號 `#include <stdint.h>`

### [問題] 2026-10-15 21:21 ❓ 未解決

【問題】手冊 HSEON 是 bit 16，標頭檔卻寫 bit 0？

- 原因：看錯成 `HSION`，兩者只差一個字母

| 名稱 | 意思 | 位置 |
|---|---|---|
| HS**I**ON | Internal 內部 8 MHz RC | bit 0 |
| HS**E**ON | External 外部石英 | bit 16 |

- 驗證：搜尋 `RCC_CR_HSEON_Pos` → `16U`
- 拿手冊和標頭檔互相核對是好習慣（IC bring-up 常要抓兩者不一致）

### [筆記] 2026-10-15 21:21

【筆記】ST 標頭檔的 bit 定義格式
**ST 每個 bit 的「三件組」定義**

- `RCC_CR_HSEON_Pos`：Position，第幾個 bit（數字）
- `RCC_CR_HSEON_Msk`：Mask，`0x1UL << Pos`，已移好位置的遮罩
- `RCC_CR_HSEON`：平常寫程式用的名字，等於 Msk
- 註解 `/*!< 0x00010000 */` 是遮罩算出的值，可快速核對
- 多個 bit 的欄位（如 PLLMUL）遮罩會是 `0xFUL << Pos`
- 寫程式用名稱，不要自己寫 `(1 << 16)`

### [問題] 2026-10-15 22:04 ❓ 未解決

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

### [解法] 2026-10-15 22:04

【解法】等待旗標 + timeout 的標準寫法
**等待 HSERDY 的正確寫法（含 timeout）**

- 推薦：直接用遮罩判斷，不移位
  - `while ((RCC->CR & RCC_CR_HSERDY_Msk) == 0U)`
- 若要移位，一律加括號：`(((RCC->CR >> Pos) & 1U) != 1U)`
- 迴圈內計數，超過 `TIME_OUT` 就 `return` 失敗，避免石英故障時卡死
- `TIME_OUT` 用 `#define TIME_OUT 5000U` 定義，數值之後依實測與 datasheet 調整
- 函式無參數要寫 `(void)`，空括號 `()` 在 C 代表「參數不確定」

### [筆記] 2026-10-15 22:04

【筆記】warning: set but not used
**`warning: variable 'hserdy' set but not used`**

- `hserdy = clock_init();` 是**寫入**（set），不是**使用**（use）
- 編譯器所說的「使用」是指**讀取**值，例如 `if (hserdy == 0U)`
- 只寫不讀 → 編譯器判定變數沒有意義 → 產生警告
- 解法：用回傳值做判斷（成功／失敗分別處理）

### [問題] 2026-10-15 22:05 ❓ 未解決

【問題】MCU 上 printf 的輸出去哪了？
**在 MCU 上呼叫 printf，字會印到哪裡？**

- MCU 沒有螢幕或終端機，`printf` 最後呼叫 `syscalls.c` 的 `_write()`
- `_write()` 再交給 `__io_putchar()`，預設沒有接到任何硬體 → 看不到輸出
- 要真的印到電腦：把 `__io_putchar` / `_write` 接到 UART（W02 USART 會做）
- 其他問題：
  - 會連結大量 C 函式庫程式碼，程式變大
  - 沒有 `\n` 時內容常卡在緩衝區，不會立即送出
- 目前做法：用 debugger 看變數與暫存器（中斷點 + Variables + SFRs）

### [問題] 2026-10-15 22:11 ❓ 未解決

【問題】ST-LINK 顯示 No device found on target
**Debug 失敗：`Error in initializing ST-LINK device. Reason: No device found on target.`**

- 意思：電腦找得到 ST-LINK，但 ST-LINK 透過 SWD 找不到 MCU
- STM32CubeProgrammer 也連不上 → 問題在**硬體連線**，不是程式或專案設定
- 本次原因：**麵包板接觸不良**，改用雙母杜邦線直接連接就成功
- 麵包板簧片會氧化、鬆脫，SWD 這類高速訊號特別容易受影響
- 燒錄／debug 失敗時，第一步先排除麵包板

### [筆記] 2026-10-15 22:11

【筆記】SWD 連不上的排查順序
**SWD 連不上 MCU 的排查順序**

1. 接線：4 條線

| ST-LINK V2 | Blue Pill |
|---|---|
| SWDIO | DIO（PA13） |
| SWCLK | CLK（PA14） |
| GND | GND（一定要接，共地） |
| 3.3V | 3.3（不要接 5V） |

2. 不經過麵包板，杜邦線直接連接，確認電源 LED 有亮
3. **BOOT0 救援法**（舊程式關掉 SWD 時使用）
   - BOOT0 跳線設 1 → 重新上電 → MCU 進入內建 Bootloader，不執行舊程式
   - CubeProgrammer 連線 → Full chip erase
   - BOOT0 改回 0 → 重新上電
   - 常見根本原因：CubeMX 的 SYS → Debug 沒設 Serial Wire，HAL 初始化時把 PA13/PA14 關掉了
4. CubeProgrammer 設定：Frequency 降到 480 kHz 以下，Mode 試 Normal / Under reset

### [筆記] 2026-10-15 22:12

【筆記】用 debugger 驗證暫存器程式
**用 debugger 驗證暫存器程式的方法**

- Debug Configuration：Main 分頁自動帶好；「调试器」分頁 = Debugger（ST-LINK GDB server、SWD）
- Startup 預設會先停在 `main()` → 按 **Resume（F8）** 跑到自己設的中斷點
- 看變數：**Variables** 或 **Expressions** 視窗
- 看硬體暫存器：**SFRs** 視窗，或 **Live Expressions** 輸入 `RCC->CR`
- 本次結果：`hserdy = 1`、HSEON = 1、HSERDY = 1 → HSE 已起振 ✅
- 直接看暫存器比看變數更有說服力（變數是程式的判斷，暫存器是硬體的實際狀態）

### [筆記] 2026-10-15 22:31

【筆記】HSE 起振實測與 TIME_OUT 怎麼決定
**HSE 起振實測：count = 209**

- 在 `return 1;` 設中斷點，觀察 `count` → 實際等了 209 圈 HSERDY 才變 1
- `TIME_OUT = 5000U`，約為實際需要的 24 倍，目前餘裕足夠
- 注意：圈數會受這些條件影響
  - 編譯最佳化：Debug `-O0` vs Release `-O2`，`-O2` 每圈更快 → 同樣時間會數到更多圈
  - 板子、石英、溫度不同
- 業界做法：用**時間**當 timeout，不用圈數（HAL 用 SysTick，HSE 預設等 100 ms）
- TODO：做完 SysTick 後，把 HSE timeout 改成以時間判斷

### [筆記] 2026-10-16 01:31

【本次進度】接下來要做Flash latency
