# 問題整理（複習與面試用）

- 「待解決」是還沒有答案的問題，附全文。
- 「踩過的錯」與「解法」只列標題，點課題名稱可以看全文。

## ❓ 待解決（0）

目前沒有。

## 踩過的錯（49）

### [SPRINT-W01-S01](notes/SPRINT-W01-S01.md) C 語言驗收

- 預測題判斷錯了 long long，理由寫成「匯流排寬度」

### [SPRINT-W01-S02](notes/SPRINT-W01-S02.md) 時脈系統（暫存器）

- RM0008是甚麼? 我要如何取得?
- 標題： RM0008 是什麼？要查哪份文件？
- 標題： STM32F103C8 屬於哪種容量等級？
- 為什麼開啟 HSE 後一定要等 HSERDY？
- F103C8 要定義哪個巨集？
- CubeIDE 2.x 找不到 New → STM32 Project
- 建立專案出現 Project location is not empty repository
- Build 成功，但狀態列顯示 Unresolved inclusion
- 手冊 HSEON 是 bit 16，標頭檔卻寫 bit 0？
- 位元運算沒加括號，等待迴圈一次都不執行
- MCU 上 printf 的輸出去哪了？
- ST-LINK 顯示 No device found on target
- 依目前值判斷要不要設定，結果設定被跳過
- ! 和 ~ 搞混，清除欄位時清掉整個暫存器
- 把其他型號才有的周邊列成 C8 的
- PLLSRC 誤選成 RCC_CFGR_SW_HSE
- 設定 bit 為 1 誤用 &
- CFGR 預期值算錯：SW/SWS 與 PLLMUL 左移
- 迴圈內歸零，timeout 永遠不會觸發
- 等待 PLLRDY 卻讀錯暫存器
- 新增的錯誤碼與既有錯誤碼同值
- 等待 SWS 時比較值沒有考慮 bit 位置
- SW 寫成 RCC->CR：沒切換卻回報成功

### [SPRINT-W01-S03](notes/SPRINT-W01-S03.md) GPIO（暫存器重做）

- main.c 出現 'CLOCK_OK' undeclared
- Build 成功，但編輯器顯示 Unresolved inclusion: "clock_init.h"
- 開 GPIO 時脈時誤用 APB2RSTR 的 mask
- GPIO 設定的兩個誤解
- LED 亮／暗用錯 Set／Reset
- 讀按鍵時沒有 mask，LED 恆暗
- PB0 誤寫成 CRH
- 複習時兩個觀念的修正
- main.c 寫成 #include "bsp_gpio.c"，連結時 multiple definition
- 按鍵函式把 Active-Low 洩漏給 main
- 讀 HAL 原始碼時的四個誤解
- 驗收時的觀念修正：CNF/MODE 與通用／複用

### [SPRINT-W01-S04](notes/SPRINT-W01-S04.md) SysTick 與 non-blocking（暫存器）

- 把 SysTick 的 TICKINT 誤解成「初始化 tick」
- SysTick 時脈來源選 72 MHz 的理由講反了
- SysTick 的 CMSIS 巨集在 stm32f103xb.h 找不到
- 想把 SysTick_Handler 加上 static 來「不公開」
- 以為 ~Msk 的值是 0
- 延遲函式用 if，沒有等待
- 改了最佳化等級，LED 現象卻沒變
- 把 BSP_GPIO_Led_Toggle() 寫進 bsp_systick 模組
- Toggle 用了 ODR 的遮罩，卻還在讀 IDR
- WasPressed() 只回傳沒清除；先清除再回傳也不對
- 以為 press_event 要加 volatile
- 改變週期後 last += period 連續補做
- 以為 now >= last + period 溢位時只是「不 toggle」

## 解法（27）

### [SPRINT-W01-S01](notes/SPRINT-W01-S01.md) C 語言驗收

- 韌體程式一律使用 <stdint.h> 的固定寬度型別

### [SPRINT-W01-S02](notes/SPRINT-W01-S02.md) 時脈系統（暫存器）

- 標題： 72 MHz 的時脈設定推導
- 石英壞了，等待迴圈會卡死
- 建立純暫存器專案的完整步驟
- 等待旗標 + timeout 的標準寫法
- 為什麼要先調 Flash latency 再升頻（驗收第 2 條）
- Flash latency 的正確寫法與驗證
- APB1 為什麼最高只能 36 MHz（驗收第 3 條）
- RCC_CFGR 預期值計算表（步驟 4）
- read-modify-write：設定幾個欄位就清除幾個
- S02 驗收回答範本（面試用）
- 上板驗證結果（步驟 5 完成）

### [SPRINT-W01-S03](notes/SPRINT-W01-S03.md) GPIO（暫存器重做）

- 複製舊專案建立新課題專案
- 單一 bit 與多 bit 欄位的寫法選擇
- PC13 設為通用推挽輸出 2 MHz
- 用 BSRR／BRR 控制 PC13 LED（Active-Low）
- PB0 上拉輸入讀按鍵、控制 PC13 LED
- 用 BSRR／BRR 控制 PC13 LED 的實作與驗證
- bsp_gpio.c 的結構與初始化順序
- LED Toggle 的寫法與風險

### [SPRINT-W01-S04](notes/SPRINT-W01-S04.md) SysTick 與 non-blocking（暫存器）

- SysTick 產生 1 ms 中斷（暫存器版）
- BSP_SysTick_GetTick() 與 volatile 的實驗驗證
- Non-blocking LED：用 BSP_SysTick_GetTick() 每 500 ms 切換
- 按鍵去彈跳狀態機設計：4 個狀態，確認按下時發事件
- 按鍵去彈跳狀態機：button_debounce 模組
- tick 溢位實驗：讓 tick 從溢位前 2 秒開始
- SPRINT-W01-S04 總整理：從頭到尾每一步

## 待學清單（1 項還沒學）

- [ ] exception stack frame（進中斷時硬體自動存的 8 個暫存器）：學 HardFault 除錯時再學（SPRINT-W01-S05）

