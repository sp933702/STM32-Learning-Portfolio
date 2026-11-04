/*
 * bsp_gpio.h
 *
 *  Created on: 2026年10月27日
 *      Author: user
 */

#ifndef BSP_GPIO_H_
#define BSP_GPIO_H_

// 有用到 bool，所以要 include
#include <stdbool.h>

void BSP_GPIO_Init(void); // BSP_GPIO_and_Button_Init 讀起來像是「GPIO」和「按鍵」是兩個不同的東西。但 LED 和按鍵都是 GPIO
// 按鍵按下時回傳 true，放開時回傳 false
bool BSP_GPIO_Button_IsPressed(void);
// 使 LED 亮，在這個專案 LED 是 active low，讓 PC13 輸出 0
void BSP_GPIO_Led_On(void);
// 使 LED 暗
void BSP_GPIO_Led_Off(void);

#endif /* BSP_GPIO_H_ */
