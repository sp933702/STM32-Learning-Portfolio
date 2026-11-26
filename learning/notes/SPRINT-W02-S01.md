# SPRINT-W02-S01：EXTI + NVIC（暫存器）

- 狀態：**進行中**
- 階段：中斷與通訊　主題：EXTI
- 進行次數：2 次（最近一次：2026-11-26）
- 程式碼：[projects/SPRINT-W02-S01](../../projects/SPRINT-W02-S01)

## 任務內容

AFIO_EXTICR 選 PB0，設定 EXTI IMR/FTSR，NVIC 設優先權並致能；ISR 中清除 PR 旗標

## 完成標準

故意不清 PR 觀察現象並解釋；能說明搶佔優先權與子優先權；ISR 該做與不該做的事

## 必學範圍

- [ ] AFIO_EXTICR 選腳位；EXTI 的 IMR、RTSR、FTSR
- [ ] PR 寫 1 清除，以及為什麼不能用讀改寫
- [ ] NVIC：致能、優先權分組、搶佔優先權與子優先權
- [ ] 向量表和 handler 名稱的對應
- [ ] ISR 該做與不該做的事
- [ ] ISR 與主迴圈共享變數：volatile、臨界區（暫時關中斷）、非原子操作造成的競爭
- [ ] 中斷延遲與巢狀中斷的概念
- [ ] 按鍵用 EXTI 和用輪詢去彈跳的比較

## 問題與筆記

### [解法] 2026-11-26 22:46

【解法】EXTI 第一步：用 AFIO_EXTICR1 把 PB0 接到 EXTI0
**先開 AFIO 時脈並讀回一次，再只改 EXTICR1 的 bit [3:0] = 0001**

- 為什麼：每個 port 的第 0 腳（PA0、PB0、PC0…）共用 EXTI line 0，由 AFIO 選接哪個 port；不設定預設是 PA0，按 PB0 完全不會觸發
- 一條 line 同一時間只能接一個 port → PA0 和 PB0 不能同時當中斷來源

| 暫存器 | 欄位（bit） | 設定值 | 代表什麼 | 為什麼選這個值 |
|---|---|---|---|---|
| `RCC->APB2ENR` | AFIOEN（0） | `1` | 開 AFIO 時脈 | 沒開時寫 AFIO 會被忽略 |
| `AFIO->EXTICR[0]` | EXTI0（3:0） | `0001` | line 0 接 PB0 | 按鍵在 PB0 |
| `AFIO->EXTICR[0]` | EXTI1～3（15:4） | 不動 | 其他 line 的來源 | 只清自己的欄位 |

- 預期值：`RCC_APB2ENR` = `0x19`（AFIOEN + IOPBEN + IOPCEN），`AFIO_EXTICR1` = `0x00000001`
- 為什麼是這個順序：先開時脈 → 讀回一次 → 才寫 EXTICR；寫 EXTICR 之後才設定 EXTI 和 NVIC，否則中斷開了卻接到 PA0

```c
void BSP_EXTI0_Init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_AFIOEN_Msk;
    (void)RCC->APB2ENR;   // errata：等開時脈的寫入完成，值一定是 1，不用檢查

    AFIO->EXTICR[0] = (AFIO->EXTICR[0] & ~AFIO_EXTICR1_EXTI0_Msk)
                    | AFIO_EXTICR1_EXTI0_PB_Msk;
}
```

### [問題] 2026-11-26 22:46

【問題】把 RCC_APB2RSTR 當成 RCC_APB2ENR，查到錯的 bit
**開時脈要看 APB2ENR（致能），描述寫「復位」的是 APB2RSTR**

- 錯在哪：查 AFIO 時脈時答成「bit 3，1 = 復位 IO 端口 B」，那是 `RCC_APB2RSTR` 的 IOPBRST
- 原因：兩個暫存器的 bit 排列幾乎一樣，只差在描述是「時鐘開啟」還是「復位」
- 正確：`RCC_APB2ENR` 的 AFIOEN 在 **bit 0**，1 = 開 AFIO 時脈
- 判斷方法：看欄位名稱結尾，`...EN` 是開時脈，`...RST` 是復位

### [問題] 2026-11-26 22:47

【問題】手冊的 AFIO_EXTICR1 寫成 AFIO->EXTICR[1]
**CMSIS 把 EXTICR1～4 宣告成陣列 EXTICR[4]，索引從 0 開始，EXTICR1 是 EXTICR[0]**

- 錯在哪：先寫 `AFIO->EXTICR1`（編譯錯誤：沒有這個成員），再改成 `EXTICR[1]`
- `EXTICR[1]` 實際上是 `AFIO_EXTICR2`（偏移 `0x0C`），會改到 EXTI4～7 的來源，EXTI0 完全沒設到
- 驗證方法：用手冊的位址偏移對 struct 的排法

| struct 成員 | 偏移 | 手冊名稱 |
|---|---|---|
| `EVCR` | `0x00` | AFIO_EVCR |
| `MAPR` | `0x04` | AFIO_MAPR |
| `EXTICR[0]` | `0x08` | AFIO_EXTICR1 |
| `EXTICR[1]` | `0x0C` | AFIO_EXTICR2 |

- 原則：CMSIS 不一定照手冊命名，編譯器報「no member named」時去 `stm32f103xb.h` 找 `XXX_TypeDef` 看實際宣告

### [問題] 2026-11-26 22:47

【問題】用 |= 寫多 bit 欄位，以及清除時把整個暫存器清掉
**多 bit 欄位要先用「欄位遮罩取反」只清自己，再 | 新值**

- 錯在哪：`AFIO->EXTICR[0] |= ..._PB_Msk`，原本是 `0010`（PC）的話會變成 `0011`（PD）
- 第二個陷阱：改成先 `& AFIO_EXTICR1_EXTI0_PA`（值是 0）→ 整個暫存器清成 0，EXTI1～3 的設定一起被清掉
- 正確：`& ~AFIO_EXTICR1_EXTI0_Msk`（`0xF`，只有 bit [3:0] 是 1）
- CMSIS 命名陷阱：`AFIO_EXTICR1_EXTI0_PB_Msk`、`..._PD_Msk` 名字叫 Msk，其實是「要寫入的值」；整個欄位的遮罩是 `AFIO_EXTICR1_EXTI0_Msk`

| 巨集 | 值 | 用途 |
|---|---|---|
| `AFIO_EXTICR1_EXTI0_Msk` | `0xF` | 欄位遮罩，取反後清除用 |
| `AFIO_EXTICR1_EXTI0_PB_Msk` | `0x1` | 寫入值：選 PB |
| `AFIO_EXTICR1_EXTI0_PD_Msk` | `0x3` | 寫入值：選 PD |

### [問題] 2026-11-26 22:48

【問題】在 .h 裡把要給 main 呼叫的函式宣告成 static
**static 函式只有同一個 .c 看得到；給別的檔案呼叫的函式不能加 static，並在 .c 裡 include 自己的 .h**

- 錯在哪：`bsp_exti.h` 寫 `static void BSP_EXTI_Init(void);`，`.c` 定義的是 `static void BSP_EXTI0_Init(void)`
- 現象：`defined but not used` 警告；main 呼叫時會找不到函式
- 名字不一致沒被抓到，是因為 `.c` 沒 include 自己的 `.h`
- 正確：公開函式不加 static、宣告放 `.h`；內部輔助函式才加 static，只寫在 `.c`（同 `bsp_gpio.c` 的 `Gpio_Clock_Enable()`）

### [問題] 2026-11-26 23:13

【問題】以為 EXTI_PR 用 |= 清除只會「碰撞」，其實會誤清其他 line
**|= 是讀→OR→寫回；在 rc_w1 的 PR 上，讀回來的 1 寫回去就等於清除，會把還沒處理的 pending 一起清掉**

- 錯在哪：以為 line 0 和 line 5 同時 pending 時，用 `|=` 會讓兩邊的值「碰撞」
- 實際過程（line 0、5 同時 pending，只想清 line 0）：

| 動作 | 值 | 說明 |
|---|---|---|
| 讀 `EXTI->PR` | `0x21` | bit 0、bit 5 都是 1 |
| `\| EXTI_PR_PR0` | `0x21` | 沒變 |
| 寫回 | `0x21` | bit 0、bit 5 都寫 1 → 兩個都被清除，line 5 的事件消失 |

- 正確：`EXTI->PR = EXTI_PR_PR0;`（其他 bit 寫 0，寫 0 沒有作用）
- PR 每個 bit 讀和寫的意義不同：硬體偵測到邊緣時設 1；軟體讀到 1 = pending；軟體寫 1 = 清除；寫 0 = 沒作用

| 暫存器類型 | 例子 | 寫法 | 原因 |
|---|---|---|---|
| rw | `RCC_APB2ENR`、`EXTI_IMR`、`EXTI_FTSR` | `\|=`／`&= ~` | 要保留其他 bit |
| rc_w1 | `EXTI_PR` | `=` | 寫 0 沒作用；讀改寫會誤清 |
| 只認寫 1 | `GPIOx_BSRR` | `=` | 寫 0 沒作用 |

### [筆記] 2026-11-26 23:14

【筆記】EXTI 的 IMR 與 EMR：中斷和事件差在哪
**IMR 開了送中斷請求給 NVIC、CPU 會跑 ISR；EMR 開了只送事件脈衝，不跑 ISR**

| 暫存器 | 開了之後 | 進 ISR | 用途 |
|---|---|---|---|
| `EXTI_IMR` | 中斷請求 → NVIC | 會 | 要 CPU 執行 handler |
| `EXTI_EMR` | 事件脈衝 | 不會 | 從 `WFE` 喚醒、觸發其他周邊 |

- line 編號 = 腳位編號：PB0 用 line 0（bit 0），port 由 AFIO 的 `EXTICR` 選
- 按鍵上拉接 GND：按下 1→0 是下降緣 → `EXTI_FTSR`；`RTSR`、`FTSR` 都設則按下、放開各觸發一次
- F1 的 EXTI 沒有 RCC 時脈開關，要開的是 AFIO（`RCC_APB2ENR` 的 AFIOEN）
