/*
 * bsp_systick.c
 *
 *  Created on: 2026年11月4日
 *      Author: user
 */

#include "bsp_systick.h"
#include "stm32f1xx.h"
// 定義 SYSCLK 的頻率，影響到計算 1ms 所需的時脈數
#include "clock_init.h"

// 1ms 需要經過 (SYSCLK_FREQ_HZ* 0.001) -1 個時脈
#define SYSTICK_LOAD_VALUE   ((SYSCLK_FREQ_HZ / 1000U) - 1U)   // 1 ms 一輪
// 條件成立（不是 0）：什麼事都沒有，不會產生任何程式碼，也不會佔 Flash。
// 條件不成立（是 0）：編譯失敗，錯誤訊息會顯示你寫的那段文字。
// LOAD 值完全由巨集 SYSCLK_FREQ_HZ 決定，編譯時就已經確定。如果它超過 24 bit，那是寫程式的人寫錯了，不是執行時才會發生的狀況，所以最好在編譯時就擋下來。
_Static_assert(SYSTICK_LOAD_VALUE <= SysTick_LOAD_RELOAD_Msk,
               "SysTick LOAD 超過 24 bit");
// tick 是一個計數器，每過 1ms 數值 +1
static volatile uint32_t tick = 0U;

void BSP_SysTick_Init(void)
{
	// 順序 : 設定 LOAD -> 設定 VAL -> 設定 CTRL
	// 選擇 72MHz 當作 HCLK，所以 1ms 需要經過 (72,000,000 * 0.001) -1 個時脈
	// 在 clock_init.h 中有定義了目前的 SYSCLK 的頻率，用這個去計算
	// SysTick -> LOAD = 71999U;
	SysTick -> LOAD = SYSTICK_LOAD_VALUE;
	// 優先權可以設 0～15，數字越小越優先。沒設的話，SysTick 的優先權維持重設值 0，也就是最高。
	// 為什麼 CMSIS 要把它設成最低：tick 晚個幾微秒加 1 完全沒差，但 UART 收資料、緊急停止按鍵這類中斷晚了就會掉資料或出事。所以 tick 要讓路給其他中斷。
	// 它實際寫的暫存器是 SCB->SHP[11]，也就是 PM0056 的 SHPR3，bit 31:24。F1 只用高 4 bit，所以 15 會寫成 0xF0。
	// 放在 LOAD 之後、VAL 之前，和 SysTick_Config() 相同：優先權要在 CTRL 打開中斷之前設好。
	NVIC_SetPriority(SysTick_IRQn, 15U);
	// VAL 初始化為 0
	SysTick -> VAL = 0U;
	// 設定 CTRL 來啟動 SysTick，CLKSOURCE 為 1，TICKINT 為 1，ENABLE 為 1
	SysTick -> CTRL = (SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_TICKINT_Msk | SysTick_CTRL_ENABLE_Msk);

}

void SysTick_Handler(void)
{
	// 讓一個 tick 計數變數 + 1
	tick ++;
}

uint32_t BSP_SysTick_GetTick(void)
{
	// 回傳 tick 數值
	return tick;
}
