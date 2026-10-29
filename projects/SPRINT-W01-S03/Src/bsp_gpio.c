/*
 * bsp_gpio.c
 *
 *  板級 GPIO 驅動：LED（PC13，Active-Low）、按鍵（PB0，按下接 GND）
 *
 *  Created on: 2026年10月27日
 *      Author: user
 */

#include "bsp_gpio.h"
#include "stm32f1xx.h"

/* ---------- 內部函式 ---------- */

// 開啟 GPIOB、GPIOC 時脈（RCC_APB2ENR 的 IOPBEN、IOPCEN）
// - F1 周邊開機時沒有時脈，沒開時對 GPIO 的寫入會被忽略
// - 用 |=：APB2ENR 也管其他周邊的時脈，不能蓋掉
static void Gpio_Clock_Enable(void)
{
    RCC->APB2ENR |= (RCC_APB2ENR_IOPBEN_Msk | RCC_APB2ENR_IOPCEN_Msk);

    // 讀回一次：等開時脈的寫入完成，才設定 GPIO（ST Errata：
    // Delay after an RCC peripheral clock enabling）。值一定是 1，不需檢查
    (void)RCC->APB2ENR;
}

// 設定 LED 腳 PC13：通用推挽輸出，最大 2 MHz（GPIOC->CRH 的 CNF13 = 00、MODE13 = 10）
// - 推挽：高低電位都主動驅動，兩種 LED 接法都能用
// - 2 MHz：LED 不需要快速切換，也是 PC13 的硬體上限
// - 呼叫前要先讓 PC13 輸出 1（先設資料再切模式），否則切成輸出時 LED 會亮一下
static void Led_Pin_Init(void)
{
    GPIOC->CRH = (GPIOC->CRH & ~(GPIO_CRH_MODE13_Msk | GPIO_CRH_CNF13_Msk))
               | GPIO_CRH_MODE13_1;
}

// 設定按鍵腳 PB0：上拉輸入（ODR bit 0 = 1，加上 GPIOB->CRL 的 CNF0 = 10、MODE0 = 00）
// - 按鍵接 GND，放開時靠上拉讀到確定的 1；浮空時讀值會亂跳
// - 先寫 ODR 再切模式：CNF = 10 由 ODR 選上拉或下拉，先切模式會短暫變成下拉
// - 用 BSRR 寫 ODR：一次寫入，不會蓋掉 GPIOB 其他腳位
static void Button_Pin_Init(void)
{
    GPIOB->BSRR = GPIO_BSRR_BS0_Msk;
    GPIOB->CRL  = (GPIOB->CRL & ~(GPIO_CRL_CNF0_Msk | GPIO_CRL_MODE0_Msk))
                | GPIO_CRL_CNF0_1;
}

/* ---------- 公開函式 ---------- */

// LED 是 Active-Low：PC13 輸出 0 才亮（BSRR 的 BR13）
void BSP_GPIO_Led_On(void)
{
    GPIOC->BSRR = GPIO_BSRR_BR13_Msk;
}

// PC13 輸出 1 → LED 暗（BSRR 的 BS13）
void BSP_GPIO_Led_Off(void)
{
    GPIOC->BSRR = GPIO_BSRR_BS13_Msk;
}

void BSP_GPIO_Init(void)
{
    Gpio_Clock_Enable();
    BSP_GPIO_Led_Off();     // 先設資料：PC13 預先輸出 1
    Led_Pin_Init();         // 再切模式：切成輸出時 LED 保持暗
    Button_Pin_Init();
}

// 按鍵按下時 PB0 接 GND，讀到 0 → 回傳 true
// - IDR 含 16 隻腳，要先和 IDR0 mask 做且運算
// - 和 0U 比較：且運算後 bit 留在原位置，不一定是 1
bool BSP_GPIO_Button_IsPressed(void)
{
    return ((GPIOB->IDR & GPIO_IDR_IDR0_Msk) == 0U);
}
