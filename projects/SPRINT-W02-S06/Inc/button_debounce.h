/*
 * button_debounce.h
 *
 *  Created on: 2026年11月9日
 *      Author: user
 */

#ifndef BUTTON_DEBOUNCE_H_
#define BUTTON_DEBOUNCE_H_

#include <stdint.h>
#include <stdbool.h>
//讓狀態機前進
void Button_Debounce_Update(uint32_t now);
// 有事件就回傳 true 並清除
bool Button_Debounce_WasPressed(void);

#endif /* BUTTON_DEBOUNCE_H_ */
