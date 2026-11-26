/*
 * bsp_exti.c
 *
 *  Created on: 2026年11月24日
 *      Author: user
 */
#include "stm32f1xx.h"
#include "bsp_exti.h"


void BSP_EXTI0_Init(void)
{
	// 賦能
	RCC -> APB2ENR |= RCC_APB2ENR_AFIOEN_Msk;
	// 讀值確認開啟
	(void)RCC -> APB2ENR;
	// 配置外部中斷暫存器 1
	AFIO -> EXTICR[0] = (AFIO -> EXTICR[0] & ~(AFIO_EXTICR1_EXTI0_Msk))
							| AFIO_EXTICR1_EXTI0_PB_Msk;

}
