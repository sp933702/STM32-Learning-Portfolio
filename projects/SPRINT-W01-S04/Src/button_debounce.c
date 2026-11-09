/*
 * button_debounce.c
 *
 *  Created on: 2026年11月9日
 *      Author: user
 */

#include "button_debounce.h"
#include "bsp_gpio.h"

// 按鍵狀態要連續保持的時間
#define BUTTON_DEBOUNCE_MS 20U

// 按鍵狀態數值化
// enum 名稱在 c 中是全域
// 結尾的 _t 代表這是一個型別的慣例，跟 uint32_t 一樣
typedef enum
{
	BUTTON_STATE_RELEASED,
	BUTTON_STATE_RELEASE_DEBOUNCE,
	BUTTON_STATE_PRESSED,
	BUTTON_STATE_PRESS_DEBOUNCE
} button_state_t;

// 開機的按鍵初始狀態
static button_state_t state = BUTTON_STATE_RELEASED;
// 開始驗證的時間
static uint32_t debounce_start = 0U;
// "按了一下"的事件旗標
static bool press_event = false;

// 讓狀態機前進
void Button_Debounce_Update(uint32_t now)
{
	// 判斷現在按鍵的狀態
	bool is_pressed = BSP_GPIO_Button_IsPressed();

	// 根據現在的按鍵狀態 + 上次紀錄的按鍵狀態來更新狀態機
	switch (state)
	{
		// 當前狀態在按鍵放開，且已經去彈跳
	    case BUTTON_STATE_RELEASED:
	        // 在 RELEASED 狀態要做的判斷
	    	if (is_pressed)
	    	{
	    		debounce_start = now;
	    		state = BUTTON_STATE_PRESS_DEBOUNCE;
	    	}
	        break;              // 做完就跳出 switch，不然會繼續往下執行下一個 case

	    case BUTTON_STATE_RELEASE_DEBOUNCE:
	        // 按鍵為放開，判斷是否超過 debounce 設定時間
	    	// 確定放開後，修改旗幟
	    	if (!is_Pressed)
	    	{
	    		if (now - debounce_start >= BUTTON_DEBOUNCE_MS)
	    		{
	    			state = BUTTON_STATE_RELEASED;
	    			// 事件只能由「消費者」（WasPressed()）清除。
	    			// 狀態機自己清的話，如果 main 那陣子在忙、還沒來得及問，這次按下就被吃掉了。
	    			// 誰產生事件、誰消費事件，責任要分清楚
	    			// press_event = false;
	    		}
	    	}
	    	// 按鍵為按下，退回按鍵已暗下的狀態
	    	else
	    	{
	    		state = BUTTON_STATE_PRESSED;
	    	}
	        break;

	    case BUTTON_STATE_PRESSED:
	    	if (!is_Pressed)
			{
				debounce_start = now;
				state = BUTTON_STATE_RELEASE_DEBOUNCE;
			}
	    	break;

		case BUTTON_STATE_PRESS_DEBOUNCE:
			// 按鍵為按下，判斷是否超過 debounce 設定時間
			// 確定放開後，修改旗幟
			if (is_Pressed)
			{
				if (now - debounce_start >= BUTTON_DEBOUNCE_MS)
				{
					state = BUTTON_STATE_PRESSED;
					press_event = true;
				}
			}
			// 按鍵為放開，退回按鍵已放開的狀態
			else
			{
				state = BUTTON_STATE_RELEASED;
			}
			break;

		// 上面都沒列到的值（理論上不會發生）
		// 防禦：回到安全的狀態
	    default:
	        state = BUTTON_STATE_RELEASED;
	        break;
	}
}
// 有事件就回傳 true 並清除
bool Button_Debounce_WasPressed(void)
{
	// 先存、再清、再回傳存起來的值
	// 把「清掉之前」的值先存起來
	// 消費掉事件
	// 回傳原本的值
	bool event = press_event;
	press_event = false;
	return event;
}
