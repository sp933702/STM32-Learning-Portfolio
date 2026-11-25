#ifndef CLOCK_INIT_H
#define CLOCK_INIT_H

// 有用到 uint32_t，所以要 include
# include <stdint.h>

// 用來標示 clock 初始化的成功與失敗
#define CLOCK_OK 0U
#define CLOCK_ERROR_HSE 1U
#define CLOCK_ERROR_PLL 2U
#define CLOCK_ERROR_SWITCH 3U

// 提供給 systick 計算幾個時脈會是 1ms 看得
#define SYSCLK_FREQ_HZ 72000000U

uint32_t Clock_Init(void);

#endif /* CLOCK_INIT_H */
