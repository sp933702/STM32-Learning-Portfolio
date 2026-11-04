/*
 * bsp_systick.c
 *
 *  Created on: 2026年11月4日
 *      Author: user
 */

#include "bsp_systick.h"
#include "stm32f1xx.h"

// tick 是一個計數器，每過 1ms 數值 +1
static volatile uint32_t tick = 0U;

void BSP_SysTick_Init(void)
{
	// 順序 : 設定 LOAD -> 設定 VAL -> 設定 CTRL
	// 選擇 72MHz 當作 HCLK，所以 1ms 需要經過 (72,000,000 * 0.001) -1 個時脈
	// VAL 初始化為 0
	// 設定 CTRL 來啟動 SysTick，CLKSOURCE 為 1，TICKINT 為 1，ENABLE 為 1
	SysTick -> LOAD = 71999U;
	SysTick -> VAL = 0U;
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

