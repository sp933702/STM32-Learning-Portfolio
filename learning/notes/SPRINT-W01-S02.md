# SPRINT-W01-S02：時脈系統（暫存器）

- 狀態：**已完成**
- 週次：W01　主題：RCC
- 對應原任務（HAL 版）：W03-S01
- 進行次數：8 次（最近一次：2026-10-20）
- 完成日期：2026-10-20
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

### [筆記] 2026-10-17 17:33

【筆記】FLASH_ACR 暫存器
**FLASH_ACR（Flash Access Control Register）**

- 查詢文件：Flash 程式設計手冊（PM0075），第三章暫存器說明
- 復位值：`0x0000 0030`

| bit | 名稱 | 屬性 | 意義 |
|---|---|---|---|
| 2:0 | LATENCY | rw | Flash 等待週期數（多 bit 欄位） |
| 4 | PRFTBE | rw | Prefetch 開關（Enable） |
| 5 | PRFTBS | r | Prefetch 狀態（Status，硬體設定） |

- 命名規律：結尾 **E** = Enable（寫）、結尾 **S** = Status（讀），同 HSEON / HSERDY
- 復位值 `0x30` = `0011 0000` → bit 4、5 = 1 → **開機預設 Prefetch 已開啟**
- 仍建議明確設定 PRFTBE：程式自帶說明，且進入程式時不一定是復位值（例如從 Bootloader 跳入）

### [筆記] 2026-10-17 17:35

【筆記】Flash 等待週期對照表
**SYSCLK 與 Flash 等待週期（WS = Wait State）**

| SYSCLK | LATENCY |
|---|---|
| 0 < SYSCLK ≤ 24 MHz | 0 WS |
| 24 < SYSCLK ≤ 48 MHz | 1 WS |
| 48 < SYSCLK ≤ 72 MHz | 2 WS |

- 本課題 SYSCLK = 72 MHz → **2 WS**
- 換算：等待週期數 = 總共需要的週期數 − 1
- 所以 SYSCLK = 72 MHz 需要等待的 Flash 週期數 = 3

### [解法] 2026-10-17 17:36

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

### [問題] 2026-10-17 18:30 ❓ 未解決

【問題】依目前值判斷要不要設定，結果設定被跳過
**`if ((FLASH->ACR & 0x30U) != 0x30U)` 裡的設定完全沒有執行**

- 復位值 `0x30` 代入：`(0x30 & 0x30) = 0x30` → `0x30 != 0x30` → **不成立**，區塊被跳過
- 誤會：把「Prefetch 已開啟」當成「Flash 已設定好」
  - 復位值 `0x30` = `0011 0000` → bit 2:0 = `000` → LATENCY 是 **0 WS**，不是 2 WS
- 後果：LATENCY 維持 0 WS，之後升到 72 MHz 就會讀錯指令 → 程式亂跑或 HardFault
- 解法：**不要依目前值決定要不要設定，直接設定**（重複寫入同一個值沒有副作用）
- 注意：括號內運算的值（48）≠ 整個條件的結果（0，不成立）

### [問題] 2026-10-17 18:30 ❓ 未解決

【問題】! 和 ~ 搞混，清除欄位時清掉整個暫存器
**`FLASH->ACR &= (!FLASH_ACR_LATENCY_Msk);` 把整個暫存器清成 0**

| 運算子 | 名稱 | `0x7` 的結果 |
|---|---|---|
| `!` | 邏輯 NOT | `0`（結果只有 0 或 1） |
| `~` | 位元 NOT | `0xFFFFFFF8`（每個 bit 反轉） |

- `&= !Msk` = `&= 0` → **32 個 bit 全部清成 0**，連 PRFTBE 也被關掉
- 正確清除欄位：`&= ~Msk` → 只清掉遮罩那幾個 bit，其他保持原樣
- `~0x7UL` 是 32 bit：`0xFFFFFFF8`（不是 `0xFFF8`），少了高位的 1 會誤清 bit 16～31

### [筆記] 2026-10-17 18:31

【筆記】ST 多 bit 欄位巨集的陷阱
**`FLASH_ACR_LATENCY_2` 不是「2 WS」**

| 巨集 | 值 | 意義 |
|---|---|---|
| `FLASH_ACR_LATENCY_Msk` | `0x7` | 整個欄位 bit 2:0 |
| `FLASH_ACR_LATENCY_0` | `0x1` | 欄位中的 bit 0 |
| `FLASH_ACR_LATENCY_1` | `0x2` | 欄位中的 bit 1 |
| `FLASH_ACR_LATENCY_2` | `0x4` | 欄位中的 bit 2 |

- 巨集名稱的數字 = **欄位中第幾個 bit**，不是設定的數值
- 2 WS = 二進位 `010` → 用 `FLASH_ACR_LATENCY_1`
- 之後的 PLLMUL、PPRE1 等多 bit 欄位也是同樣的命名方式

### [解法] 2026-10-17 18:31

【解法】Flash latency 的正確寫法與驗證
**FLASH_ACR 設定：Prefetch 開啟 + 2 WS**

- 開啟 Prefetch：`FLASH->ACR |= FLASH_ACR_PRFTBE_Msk;`
- 設定 LATENCY（read-modify-write，一行完成）：
  - `FLASH->ACR = (FLASH->ACR & ~FLASH_ACR_LATENCY_Msk) | FLASH_ACR_LATENCY_1;`
- 通用公式：`REG = (REG & ~欄位Msk) | 新值;`
- 為什麼不能只用 `|=`：舊值 `001` |= `010` → `011`，舊的 bit 殘留
- 不要寫 PRFTBS：它是 **r（唯讀）**，硬體回報狀態，寫入無效
- 驗證：預期 `0011 0010` = **0x32 = 50**，debugger 實際值 50 ✅

### [筆記] 2026-10-17 18:32

【筆記】驗證的原則：先獨立算出預期值
**錯的程式通過了錯的驗證**

- 第一版程式：設定被跳過，實際值 48（0x30）
- 預期值也算成 `110000`（漏了 LATENCY 的 `010`）→ 兩者「相同」，誤以為成功
- 原則：
  - 寫程式前，先**根據手冊獨立算出**預期的暫存器值（每個欄位逐一列出）
  - 再用 debugger 比對實際值
  - 不能看到實際值之後才去對答案
- 實務上「錯的程式 + 錯的驗證」最危險，因為不會有任何錯誤訊息

### [筆記] 2026-10-17 22:42

【筆記】RCC_CFGR 欄位與 72 MHz 設定值
**RCC_CFGR（時脈設定暫存器）：72 MHz 要設定的欄位**

| 欄位 | bit | 設定值 | 意義 |
|---|---|---|---|
| PLLSRC | 16 | `1` | PLL 輸入選 HSE |
| PLLXTPRE | 17 | `0` | HSE 進 PLL 前 ÷1 |
| PLLMUL | 21:18 | `0111` | ×9 |
| HPRE | 7:4 | `0000` | AHB ÷1 |
| PPRE1 | 10:8 | `100` | APB1 ÷2 |
| PPRE2 | 13:11 | `000` | APB2 ÷1 |

- PLLMUL 的**設定值不等於倍數**：×9 是 `0111`（7），要查對照表
- 手冊中的 `x` = don't care：例如 HPRE `0xxx`，只要 bit 7 = 0 就是不分頻
- 寫程式時 `x` 一律寫 0：跟復位值一致、debugger 好比對、不留意義不明的 bit

### [筆記] 2026-10-17 22:42

【筆記】PLL 的開關與設定限制
**PLL 開關（RCC_CR）與設定順序**

| bit | 名稱 | 屬性 | 意義 |
|---|---|---|---|
| 24 | PLLON | rw | 1 = 開啟 PLL |
| 25 | PLLRDY | r | 1 = PLL 已鎖定（硬體設定） |

- 命名規律同 HSEON / HSERDY：ON = 開關、RDY = 就緒旗標
- 限制：PLLSRC、PLLXTPRE、PLLMUL 必須在 **PLLON = 0** 時設定，開啟後不能修改
  - 手冊沒有 PLLOFF 這個 bit，「關閉」就是 PLLON = 0
  - 開機時 PLL 預設是關閉的
- 正確順序：設定 PLL 參數 → PLLON = 1 → 等 PLLRDY = 1
- 另一個限制：PLL 正在當 SYSCLK 時不能關掉；要改設定必須先把 SYSCLK 切回 HSI/HSE

### [解法] 2026-10-17 22:43

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

### [問題] 2026-10-17 22:44 ❓ 未解決

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

### [問題] 2026-10-19 22:12 ❓ 未解決

【問題】PLLSRC 誤選成 RCC_CFGR_SW_HSE
**「PLL 輸入選 HSE」誤用 `RCC_CFGR_SW_HSE`**

- 時脈樹上有**兩個**梯形選擇器，用途不同：

| 選擇器 | 位置 | 決定什麼 | 巨集 |
|---|---|---|---|
| PLLSRC | PLL **前面** | PLL 的輸入來源 | `RCC_CFGR_PLLSRC_Msk` |
| SW | SYSCLK **前面** | 系統時脈的來源 | `RCC_CFGR_SW_HSI / HSE / PLL` |

- `RCC_CFGR_SW_HSE` = 把 SYSCLK 直接切到 HSE，跟 PLL 無關
- 找巨集前先回到時脈樹確認：要設定的是**哪一個**選擇器

### [問題] 2026-10-19 22:12 ❓ 未解決

【問題】設定 bit 為 1 誤用 &
**要把 PLLSRC 設成 1，誤以為要用 `&`**

| 目的 | 寫法 | 效果 |
|---|---|---|
| 設成 1 | `REG \|= Msk` | 只有遮罩的 bit 變 1，其他不變 |
| 清成 0 | `REG &= ~Msk` | 只有遮罩的 bit 變 0，其他不變 |
| 檢查 | `(REG & Msk) != 0U` | 讀取，不修改暫存器 |

- 錯誤寫法 `REG &= Msk`：**除了遮罩的 bit，其他全部被清成 0**
- 口訣：`|=` 設定、`&= ~` 清除、`&` 檢查

### [筆記] 2026-10-19 22:13

【筆記】值為 0 的巨集：RCC_CFGR_PLLXTPRE_HSE
**`RCC_CFGR_PLLXTPRE_HSE` 的值是 0**

- `RCC_CFGR_PLLXTPRE_HSE` = `0x00000000`（HSE ÷1）
- `RCC_CFGR_PLLXTPRE_HSE_DIV2` = `0x00020000`（HSE ÷2）
- `|=` 一個 0 不會改變任何 bit → 真正讓它變成 ÷1 的是**先清除欄位**（`& ~Msk`）
- 仍然寫上這個巨集：**表達意圖**，讀程式的人一看就知道選的是 ÷1
- 同理：`RCC_CFGR_HPRE_DIV1`、`RCC_CFGR_PPRE2_DIV1` 的值也都是 0

### [問題] 2026-10-19 22:13 ❓ 未解決

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

### [解法] 2026-10-19 22:13

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

### [筆記] 2026-10-19 22:14

【筆記】錯誤碼設計：成功 = 0，錯誤 = 非 0
**函式有多個失敗點時，用錯誤碼回傳**

- `#define CLOCK_OK 0U`、`#define CLOCK_ERR_HSE 1U`、`#define CLOCK_ERR_PLL 2U`
- 為什麼成功用 0：
  - 成功只有一種，失敗可能有很多種
  - `if (ret != CLOCK_OK)` 一次抓到所有錯誤，新增錯誤碼也不用改判斷
  - 需要細分時再看 `ret` 的值
- 業界同樣做法：HAL 的 `HAL_OK = 0`、`HAL_ERROR`、`HAL_TIMEOUT`
- 為什麼不用兩個 0/1 旗標（如 `hse_ok`、`pll_ok`）：
  - 2 × 2 = 4 種組合，但有意義的只有 3 種
  - 「HSE 失敗、PLL 成功」不可能發生（HSE 失敗會先 return），程式卻還是得處理
  - `pll_ok = 0` 分不出是「失敗」還是「根本沒執行」
- 設計原則：**讓不合法的狀態根本表示不出來**（make illegal states unrepresentable）

### [問題] 2026-10-19 23:16 ❓ 未解決

【問題】迴圈內歸零，timeout 永遠不會觸發
**`count = 0U;` 寫在 while 迴圈裡，timeout 永遠不會觸發**

- 錯誤寫法：每圈先 `count = 0U` 再 `count++` → 每圈結束 count 都是 1，永遠到不了 5000
- 後果：等待條件不成立時程式永遠卡死，timeout 形同虛設
- 解法：
  - `count = 0U;` 放在迴圈**前面**
  - 第二個等待迴圈之前要**重新歸零**（第一個迴圈結束時 count 約 209）
- 檢查方法：在腦中跑三圈，寫出每圈結束時變數的值

### [問題] 2026-10-19 23:16 ❓ 未解決

【問題】等待 PLLRDY 卻讀錯暫存器
**`while ((RCC->CFGR & RCC_CR_PLLRDY_Msk) == 0U)` 永遠等不到**

- PLLRDY 在 **RCC_CR** 的 bit 25，不是 RCC_CFGR
- CFGR 的 bit 25 是 **MCO** 欄位的一部分，目前為 0 → 條件永遠成立
- 加上 ㊲ 的歸零 bug → 程式永遠卡在這個迴圈
- 巨集名稱已經寫明暫存器：`RCC_CR_PLLRDY_Msk` 要配 `RCC->CR`
- 習慣：每寫一個位元運算，確認「**哪個暫存器的哪個 bit**」，巨集前綴要跟暫存器一致

### [筆記] 2026-10-19 23:16

【筆記】RCC_CR 實測值解讀（步驟 4 完成時）
**`RCC->CR` = 50562691 = `0x03038683`**

| bit | 值 | 意義 |
|---|---|---|
| 25、24 | `11` | PLLRDY = 1、PLLON = 1 → PLL 已鎖定 |
| 17、16 | `11` | HSERDY = 1、HSEON = 1 |
| 15:8 | `0x86` | HSICAL：ST 出廠校正值，每顆晶片不同 |
| 7:3 | `10000` | HSITRIM：預設微調值 |
| 1、0 | `11` | HSIRDY = 1、HSION = 1（SYSCLK 仍在用 HSI） |

- `RCC->CFGR` = `0x001D0400`，與預期一致
- 實測等待圈數：HSE 起振 **209** 圈、PLL 鎖定 **31** 圈
- Expressions 顯示 Error：變數已改名或運算式括號不完整，刪除即可

### [解法] 2026-10-19 23:16

【解法】read-modify-write：設定幾個欄位就清除幾個
**CFGR 只清除了 PLLXTPRE，其他 5 個欄位沒清**

- 現在剛好能動：開機時這些欄位都是 0
- 以後會出事：從 Bootloader 跳入、或函式執行第二次時，舊 bit 殘留（同 `001 | 010 = 011`）
- 正確寫法：

`RCC->CFGR = (RCC->CFGR & ~(RCC_CFGR_PLLSRC_Msk | RCC_CFGR_PLLXTPRE_Msk | RCC_CFGR_PLLMULL_Msk | RCC_CFGR_HPRE_Msk | RCC_CFGR_PPRE1_Msk | RCC_CFGR_PPRE2_Msk)) | (6 個設定值);`

- 原則：**清除的欄位與設定的欄位一一對應**
- 結構：`REG = (REG & ~(清除清單)) | (設定清單);`，不要混用 `&`、`|` 卻不加括號

### [問題] 2026-10-19 23:16 ❓ 未解決

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

### [問題] 2026-10-19 23:17 ❓ 未解決

【問題】等待 SWS 時比較值沒有考慮 bit 位置
**`while ((RCC->CFGR & RCC_CFGR_SWS_Msk) != 2U)` 切換成功也會 timeout**

- SWS 在 **bit 3:2**，`& Msk` 後數值**仍在原位置、沒有右移**
- SWS = `10` → `0000 1000` = **`0x8`**，永遠不等於 2
- 後果：明明切換成功，卻跑到 timeout，回傳「切換失敗」
- 解法：用巨集比較，位置已算好
  - `while ((RCC->CFGR & RCC_CFGR_SWS_Msk) != RCC_CFGR_SWS_PLL)`
- 同類錯誤：㉞ 的 PLLMUL 左移；**比較欄位值時一律用巨集，不要自己寫數字**
- 也不能寫 `== 0U`：SWS 為 `01`（HSE）時同樣不是 0，要比對的是「**等於 PLL**」

### [筆記] 2026-10-19 23:17

【筆記】SW 與 SWS：一個寫、一個讀
**系統時脈切換：SW（寫）與 SWS（讀）**

| 欄位 | bit | 屬性 | 巨集（選 PLL） | 值 |
|---|---|---|---|---|
| SW | 1:0 | rw | `RCC_CFGR_SW_PLL` | `0x2` |
| SWS | 3:2 | r | `RCC_CFGR_SWS_PLL` | `0x8` |

- 對照：`00` = HSI、`01` = HSE、`10` = PLL
- SW 是「要求」，SWS 是硬體回報「實際正在使用」的時脈；寫入 SW 後要等 SWS 跟上
- 同樣模式：HSEON/HSERDY、PLLON/PLLRDY、PRFTBE/PRFTBS
- 不要寫入 SWS（唯讀）
- 用 `RCC_CFGR_SW_PLL`，不要用 `RCC_CFGR_SW_1`：值相同（0x2），但 `_1` 代表「第 1 個 bit」，讀不出意圖
- 切換完成後 CFGR 預期值：`0x001D0400 | 0x2 | 0x8` = **`0x001D040A`**

### [問題] 2026-10-20 22:48 ❓ 未解決

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

### [筆記] 2026-10-20 22:49

【筆記】只看回傳值不夠，要直接看暫存器
**驗證時為什麼一定要看 SWS，不能只看 `clock_state`？**

- `clock_state` 是程式自己的判斷，程式寫錯時判斷也會錯
- ㊾ 的實例：SW 寫錯暫存器，等待條件又剛好成立 → `clock_state = CLOCK_OK`，但 SYSCLK 仍是 8 MHz
- 不當機、不報錯、回傳值正常 → **最危險的一種錯誤**
- 暫存器（SWS）是**硬體回報的實際狀態**，才是真正的證據
- 這就是完成標準要求「用 debugger 確認 SWS」的原因
- 原則：驗證要看**硬體狀態**，不要只相信軟體的判斷

### [筆記] 2026-10-20 22:49

【筆記】切換時脈的設定順序：任何時刻都要在規格內
**切換時脈時，Flash latency 與 APB 分頻的順序**

- 原則：**任何時刻，每個時脈都要在規格內**（Flash 夠時間讀、PCLK1 ≤ 36 MHz）
- 比喻：SYSCLK = 總水壓、APB 分頻 = 減壓閥、APB1 支管上限 36；一次只能動一個

| 寫法 | 升頻 8 → 72 | 降頻 72 → 8 |
|---|---|---|
| 先設目標分頻，再切換（自寫） | ✅ PCLK1：8 → 4 → 36 | ❌ 瞬間 72 |
| 先切換，再設分頻 | ❌ 瞬間 72 | ✅ PCLK1：36 → 4 → 8 |
| HAL：先 ÷16 → 切換 → 設目標 | ✅ 最高 4.5 | ✅ 最高 4.5 |

- 前兩種寫法都要**先知道升頻或降頻**，選錯就超規格
- HAL 先把 APB 分頻設成 ÷16：不管怎麼切，PCLK 最高 72 ÷ 16 = 4.5 MHz，**不用判斷方向**
- HAL 降的是**匯流排分頻**，不是 SYSCLK；SYSCLK 照常切換
- 自寫 `clock_init()` 只在開機執行、永遠是升頻 → 「先設 ÷2 再切換」已足夠
- 同一原則用在 Flash latency：升頻先加 WS、降頻後減 WS（㉑）

### [筆記] 2026-10-20 22:50

【解法】S02 驗收回答範本（面試用）
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

### [解法] 2026-10-20 22:50

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

### [筆記] 2026-10-20 22:51

【筆記】自寫 clock_init() 與 HAL 版比較
**`clock_init()` vs HAL `SystemClock_Config()`**

| 項目 | 自寫 `clock_init()` | HAL |
|---|---|---|
| 結構 | 一個函式，依序設定 | `RCC_OscInitStruct`（時脈怎麼產生）＋ `RCC_ClkInitStruct`（時脈怎麼分配） |
| 適用範圍 | 只做 HSE → PLL 72 MHz | 支援所有時脈源與任意升降頻 |
| timeout | 迴圈圈數 | 時間（`HAL_GetTick()`，HSE 100 ms、PLL 2 ms、切換 5 s） |
| Flash latency | 切換前設定一次 | 升頻在切換前、降頻在切換後；設定後**讀回檢查** |
| APB 分頻 | 切換前直接設成 ÷2 | 切換前暫設 **÷16**，切換後才設目標值 |
| 切換後 | 無 | 更新 `SystemCoreClock`、`HAL_InitTick()` 重設 SysTick |
| 錯誤處理 | `CLOCK_OK` / `CLOCK_ERROR_xxx` | `HAL_OK` / `HAL_ERROR` / `HAL_TIMEOUT` → `Error_Handler()` |

- 自寫版：簡短、每個 bit 都清楚，適合固定用途的開機初始化
- HAL 版：通用、保守，代價是程式碼長、依賴 SysTick
- HAL 原始碼：`STM32Cube_FW_F1_V1.8.7\Drivers\STM32F1xx_HAL_Driver\Src\stm32f1xx_hal_rcc.c`

### [筆記] 2026-10-20 22:52

【筆記】timeout 用時間比用圈數好
**為什麼 timeout 要用時間，不用圈數？**

- 一圈的時間會變：
  - 編譯最佳化：`-O2` 比 `-O0` 快
  - 時脈頻率：同一段程式在 72 MHz 比 8 MHz 快 9 倍
- 同樣寫 5000 圈，實際等待時間可能差十倍以上，且無法從程式看出等了多久
- 用時間：寫 100 ms 就是 100 ms，與編譯選項、時脈無關
- Datasheet 的起振時間規格本來就以時間表示，可直接對照
- 實測：HSE 209 圈 ≈ 0.39 ms（以每圈 15 個週期、8 MHz 估算）；HAL 給 100 ms，約 250 倍餘裕
- TODO：做完 SysTick 後改成以時間判斷

### [筆記] 2026-10-20 22:52

【筆記】時脈改變後為什麼要更新 SystemCoreClock 與 SysTick
**切換時脈後，HAL 多做的兩件事**

- `SystemCoreClock`：存放目前 HCLK 頻率（Hz），其他程式靠它計算
  - SysTick 1 ms 的重載值、UART 鮑率、`HAL_Delay()` 的時間基準
  - 時脈改了卻沒更新 → 這些計算全部錯誤
- `HAL_InitTick()`：依新頻率重設 SysTick
  - 原本依 8 MHz 設定：8000 個週期 = 1 ms
  - 切到 72 MHz 後：8000 個週期 = 8000 ÷ 72 MHz ≈ **0.111 ms**
  - 不重設的話，`HAL_Delay(1000)` 實際只延遲約 **111 ms**
- 注意：Empty 專案沒有 `system_stm32f1xx.c`，目前沒有 `SystemCoreClock`，下一個課題做 SysTick 時要自己處理

### [筆記] 2026-10-20 23:01

**STM32 開機一律從 HSI 8 MHz 開始**

- reset 後 RCC 回到復位值：`RCC_CR` HSION = 1、`RCC_CFGR` = `0x00000000`（SW = SWS = `00` = HSI）
- 設計理由：HSI 在晶片內部，不需外部零件，石英壞了 MCU 也能開機，再由程式決定是否切換
- 會回到 HSI 的情況：上電、NRST、軟體重置、看門狗重置、Standby 喚醒
- 例外：
  - Stop 喚醒不是 reset，但硬體會把 SYSCLK 切回 HSI → 醒來要再呼叫 `clock_init()`
  - 從 Bootloader 跳入時，時脈可能已被改過，不是復位值 → 要清除後再設定（㊵）
- 驗證：在 `clock_init()` 之前設中斷點，`RCC->CFGR` 應為 `0x00000000`

### [筆記] 2026-10-20 23:07

**S02 縮寫總表**

### 時脈來源
| 縮寫 | 英文全名 | 中文說明 |
|---|---|---|
| HSI | High-Speed Internal | 內部高速振盪器，8 MHz RC，開機預設 |
| HSE | High-Speed External | 外部高速振盪器，本板接 8 MHz 石英 |
| LSI | Low-Speed Internal | 內部低速振盪器，40 kHz，給 IWDG 用 |
| LSE | Low-Speed External | 外部低速石英，32.768 kHz，給 RTC 用 |
| PLL | Phase-Locked Loop | 鎖相迴路，把輸入時脈倍頻（本課題 ×9） |
| RC | Resistor-Capacitor | 電阻電容振盪電路（HSI、LSI 的類型） |
| OSC | Oscillator | 振盪器 |

### 時脈與匯流排
| 縮寫 | 英文全名 | 中文說明 |
|---|---|---|
| SYSCLK | System Clock | 系統時脈，本課題 72 MHz |
| HCLK | AHB Clock | AHB 匯流排時脈（CPU、記憶體），72 MHz |
| PCLK1 | Peripheral Clock 1 | APB1 周邊時脈，上限 36 MHz |
| PCLK2 | Peripheral Clock 2 | APB2 周邊時脈，上限 72 MHz |
| AHB | Advanced High-performance Bus | 高效能匯流排 |
| APB | Advanced Peripheral Bus | 周邊匯流排（APB1 低速、APB2 高速） |
| MCO | Microcontroller Clock Output | 把內部時脈輸出到腳位（CFGR bit 26:24） |
| MUX | Multiplexer | 多工器／選擇器，時脈樹上的梯形 |

### 暫存器
| 縮寫 | 英文全名 | 中文說明 |
|---|---|---|
| RCC | Reset and Clock Control | 重置與時脈控制周邊 |
| CR | Clock Control Register | RCC_CR：時脈開關與就緒旗標 |
| CFGR | Clock Configuration Register | RCC_CFGR：PLL、分頻、時脈切換設定 |
| ACR | Access Control Register | FLASH_ACR：Flash 等待週期與預取 |
| SFR | Special Function Register | 特殊功能暫存器（debugger 的 SFRs 視窗） |

### 暫存器欄位（bit 名稱）
| 縮寫 | 英文全名 | 中文說明 |
|---|---|---|
| HSEON / HSION / PLLON | … ON | 開關，寫 1 開啟（rw） |
| HSERDY / HSIRDY / PLLRDY | … Ready | 就緒旗標，硬體設定（r） |
| HSEBYP | HSE Bypass | 旁路：直接吃外部時脈訊號（接石英設 0） |
| HSITRIM | HSI Trimming | HSI 微調值（CR bit 7:3） |
| HSICAL | HSI Calibration | HSI 出廠校正值（CR bit 15:8） |
| PLLSRC | PLL Source | PLL 輸入來源（HSI÷2 或 HSE） |
| PLLXTPRE | PLL XT Prescaler | HSE 進 PLL 前的分頻（÷1／÷2），XT = 石英 |
| PLLMUL | PLL Multiplication factor | PLL 倍數（×9 = `0111`）；巨集寫作 PLLMULL |
| HPRE | AHB (HCLK) Prescaler | AHB 分頻 |
| PPRE1 / PPRE2 | APB1 / APB2 Prescaler | APB1／APB2 分頻 |
| SW | System clock Switch | 系統時脈選擇（rw） |
| SWS | System clock Switch Status | 系統時脈實際狀態（r） |
| LATENCY | Flash Latency | Flash 等待週期數（ACR bit 2:0） |
| PRFTBE | Prefetch Buffer Enable | 預取緩衝開關（rw） |
| PRFTBS | Prefetch Buffer Status | 預取緩衝狀態（r） |
| WS | Wait State | 等待週期（72 MHz 需 2 WS） |

### 命名規律與巨集後綴
| 寫法 | 意義 |
|---|---|
| …ON／…RDY | 開關（寫）／就緒旗標（讀） |
| …E／…S | Enable（寫）／Status（讀） |
| `_Pos` | Position：欄位從第幾個 bit 開始 |
| `_Msk` | Mask：已移好位置的遮罩 |
| `_0`、`_1`、`_2` | 欄位中的第幾個 bit（不是設定值） |
| `_DIV2`、`_PLL`、`MULL9` | 有意義的設定值巨集（優先使用） |
| `U`／`UL` | unsigned／unsigned long 的數字後綴 |
| `x`（手冊中） | don't care，寫程式時一律寫 0 |
| rw／r／res | 可讀寫／唯讀／保留不可動 |

### 文件與軟體
| 縮寫 | 英文全名 | 中文說明 |
|---|---|---|
| RM0008 | Reference Manual | F10x 參考手冊：周邊與暫存器定義 |
| PM0056 | Programming Manual | Cortex-M3 程式設計手冊：NVIC、SysTick |
| PM0075 | Programming Manual | Flash 程式設計手冊：FLASH_ACR |
| DS | Datasheet | 資料手冊：腳位、電氣特性、頻率上限、實際周邊 |
| CMSIS | Cortex Microcontroller Software Interface Standard | Arm 標準介面，提供暫存器定義標頭檔 |
| HAL | Hardware Abstraction Layer | ST 的硬體抽象層函式庫 |
| MISRA C | Motor Industry Software Reliability Association | 嵌入式 C 程式碼規範 |
| IDE | Integrated Development Environment | 整合開發環境（STM32CubeIDE） |
| ELF | Executable and Linkable Format | 編譯產生的執行檔格式（.elf） |
| RMW | Read-Modify-Write | 讀取 → 修改 → 寫回，`REG = (REG & ~Msk) | 值` |

### 燒錄與除錯
| 縮寫 | 英文全名 | 中文說明 |
|---|---|---|
| SWD | Serial Wire Debug | 兩線式除錯介面 |
| SWDIO | Serial Wire Debug I/O | SWD 資料線（PA13） |
| SWCLK | Serial Wire Clock | SWD 時脈線（PA14） |
| ST-LINK | — | ST 的燒錄／除錯器 |
| GDB | GNU Debugger | CubeIDE 背後的除錯程式 |
| NRST | Reset pin（低電位有效） | 重置腳 |
| BOOT0 | Boot mode pin 0 | 開機模式腳，設 1 進入內建 Bootloader |

### 晶片與系統
| 縮寫 | 英文全名 | 中文說明 |
|---|---|---|
| MCU | Microcontroller Unit | 微控制器 |
| CPU | Central Processing Unit | 中央處理器（Cortex-M3 核心） |
| NVIC | Nested Vectored Interrupt Controller | 巢狀向量中斷控制器 |
| SysTick | System Tick Timer | Cortex-M 內建的系統計時器 |
| HardFault | — | 硬體錯誤例外，例如讀到錯誤指令 |
| IWDG | Independent Watchdog | 獨立看門狗（用 LSI） |
| WWDG | Window Watchdog | 窗口看門狗 |
| RTC | Real-Time Clock | 即時時鐘（用 LSE） |
| LD／MD／HD | Low／Medium／High Density | 小／中／大容量（C8 = 64 KB = MD） |

### 本課題提到的周邊
| 縮寫 | 英文全名 | 所在匯流排 |
|---|---|---|
| GPIO | General-Purpose I/O | APB2 |
| AFIO | Alternate Function I/O | APB2 |
| ADC | Analog-to-Digital Converter | APB2 |
| TIM | Timer（TIM1 高級、TIM2～4 一般） | TIM1 在 APB2；TIM2～4 在 APB1 |
| USART | Universal Synchronous/Asynchronous Receiver Transmitter | USART1 在 APB2；USART2、3 在 APB1 |
| SPI | Serial Peripheral Interface | SPI1 在 APB2；SPI2 在 APB1 |
| I²C | Inter-Integrated Circuit | APB1 |
| CAN | Controller Area Network | APB1 |
| USB | Universal Serial Bus | APB1（需要 48 MHz） |
| PWR／BKP | Power control／Backup | APB1 |

### 單位與電路概念
| 縮寫 | 說明 |
|---|---|
| MHz／kHz | 百萬赫茲／千赫茲 |
| ns／µs／ms | 奈秒／微秒／毫秒，1 µs = 1000 ns；週期（ns）= 1000 ÷ 頻率（MHz） |
| FF | Flip-Flop，正反器 |
| Timing closure | 時序收斂：訊號要在一個週期內傳到下一個正反器 |
| Bring-up | 晶片初次上電驗證 |

### [筆記] 2026-10-20 23:09

**從開機到 clock_init() 完成的流程（SPRINT-W01-S02 專案實測）**

圖例：⭐ = S02 本課學到的內容　🔜 = 預習，之後課題會深入（W01 Startup／Linker Script）

---

**0. 上電／Reset（硬體）⭐**
- ⭐ 暫存器回到**復位值**：
  - ⭐ `RCC_CR`：HSION = 1、HSIRDY = 1 → HSI 8 MHz 開啟；HSE、PLL 關閉
  - ⭐ `RCC_CFGR` = `0x00000000` → SW = SWS = `00` → **SYSCLK = HSI**
  - ⭐ `FLASH_ACR` = `0x30` → 0 WS、Prefetch 開啟
- ⭐ 設計理由：HSI 在晶片內部，石英壞了 MCU 也能開機
- ⭐ 會回到 HSI 的情況：上電、NRST、軟體重置、看門狗、Standby 喚醒；Stop 喚醒也會切回 HSI

**1. 讀 BOOT0（硬體）⭐**
- BOOT0 = 0 → 從主 Flash（0x0800_0000）開機
- ⭐ BOOT0 = 1 → 進入 ST 內建 Bootloader，不執行自己的程式（SWD 救援法，⑮）

**2. 讀向量表 `g_pfnVectors`（硬體）🔜**
- 🔜 0x0800_0000：`_estack` = `0x2000_5000` → 載入 SP（堆疊指標）
- 🔜 0x0800_0004：`Reset_Handler` = `0x0800_0271` → 載入 PC（最低位 1 = Thumb 模式）

**3. Reset_Handler：設定 SP（啟動檔）🔜**

**4. `bl SystemInit`：本專案中被換成 `nop.w` 🔜**
- 🔜 啟動檔宣告 `.weak SystemInit`：找不到定義時，連結器把呼叫換成 NOP
- 🔜 證據：`.list` 檔中 `bl SystemInit` → `8000274: f3af 8000 nop.w`
- 🔜 所以進入 `main()` 時時脈是復位狀態，也沒有 `SystemCoreClock`
- 🔜 HAL 專案的 `SystemInit()` 會重設 RCC、設定向量表位置

**5. 準備 C 執行環境（啟動檔）🔜**
- 🔜 複製 `.data`：有初始值的全域變數，Flash（`_sidata`）→ RAM（`_sdata`～`_edata`）
- 🔜 清零 `.bss`：沒有初始值的全域變數，RAM（`_sbss`～`_ebss`）寫 0
- 🔜 `__libc_init_array`：C 函式庫初始化
- 🔜 `bl main`

**6. `main()` → `clock_init()` ⭐⭐ 本課主體**

| 步驟 | 暫存器 | 等待 | 失敗回傳 |
|---|---|---|---|
| ⭐ HSE 開啟 | CR HSEON | HSERDY（209 圈） | `CLOCK_ERROR_HSE` |
| ⭐ Flash 2 WS + Prefetch | ACR = `0x32` | — | — |
| ⭐ PLL 與分頻 | CFGR = `0x001D0400` | — | — |
| ⭐ PLL 開啟 | CR PLLON | PLLRDY（31 圈） | `CLOCK_ERROR_PLL` |
| ⭐ 切換 SYSCLK | CFGR SW = PLL | SWS = PLL（0 圈） | `CLOCK_ERROR_SWITCH` |
| ⭐ 完成 | CFGR = `0x001D040A` | — | `CLOCK_OK` |

- ⭐ 順序原則：**任何時刻每個時脈都要在規格內**
  - ⭐ 先設 Flash latency，再升頻（㉑）
  - ⭐ 先設 APB1 ÷2，再切換 SW（51）
  - ⭐ PLL 參數要在 PLLON = 0 時設定（㉘）
- ⭐ 每個等待都有 timeout，避免石英或 PLL 故障時卡死（㊲）
- ⭐ 驗證要看 SWS，不能只看回傳值（㊿）

**7. 回到 `main()`**
- ⭐ 失敗停在 `while (clock_state != CLOCK_OK)`；成功進入 `for(;;)`
- 🔜 `main()` 若 return → 啟動檔 `LoopForever` 無窮迴圈（MCU 沒有作業系統可回）

---

**相關檔案**
- ⭐ `Src/main.c`：`clock_init()`
- ⭐ `Inc/CMSIS/stm32f103xb.h`：暫存器結構與 bit 巨集
- 🔜 `Startup/startup_stm32f103c8tx.s`：向量表、`Reset_Handler`
- 🔜 `STM32F103C8TX_FLASH.ld`：記憶體配置（FLASH 64K @ 0x0800_0000、RAM 20K @ 0x2000_0000）、`_estack`
- 🔜 `Debug/SPRINT-W01-S02.list`：反組譯結果，可看到實際的指令與位址
