/*
 * bsp_systick.h
 *
 *  Created on: 2026年11月4日
 *      Author: user
 */

#ifndef BSP_SYSTICK_H_
#define BSP_SYSTICK_H_

#include <stdint.h>

// 初始化 SysTick
void BSP_SysTick_Init(void);

// 知道初始化後到現在過了多少 ms
uint32_t BSP_SysTick_GetTick(void);

// 實驗用
// 阻塞延遲
void BSP_SysTick_Delay(uint32_t ms);
#endif /* BSP_SYSTICK_H_ */
