from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import config

# 모든 식당의 데이터를 저장 (main에서 갱신)
current_menus = {}

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_text = update.message.text

    # 1. "급식" 입력 시 식당 선택 버튼 출력 (2열 배치)
    if "급식" in user_text and user_text not in config.CAFETERIAS:
        names = list(config.CAFETERIAS.keys())
        keyboard = [names[i:i+2] for i in range(0, len(names), 2)]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("조회할 식당을 선택해주세요:", reply_markup=reply_markup)
        return

    # 2. 선택한 식당의 식단 출력
    if user_text in config.CAFETERIAS:
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        today_idx = datetime.now().weekday()
        target_day = weekdays[today_idx]

        if today_idx >= 6:
            await update.message.reply_text("오늘은 일요일입니다. 주말엔 휴무입니다! 🍕")
            return

        cafeteria_data = current_menus.get(user_text, {})
        day_data = cafeteria_data.get(target_day, {})

        if day_data:
            lunch = day_data.get('중식', '정보가 없습니다.')
            dinner = day_data.get('석식', '정보가 없습니다.')
            msg = (
                f"🍴 오늘({target_day}) [{user_text}] 식단\n"
                f"━━━━━━━━━━━━━━\n"
                f"☀️ [중식]\n{lunch}\n\n"
                f"🌙 [석식]\n{dinner}\n"
                f"━━━━━━━━━━━━━━"
            )
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"{user_text}의 {target_day}요일 식단 정보가 없습니다.")