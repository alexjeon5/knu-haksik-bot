from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode 
from telegram.ext import ContextTypes
from datetime import datetime
import config

current_menus = {}

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_text = update.message.text.strip()

    # 입력된 텍스트에서 실제 식당 이름 추출
    target_cafeteria = None
    for cafe in config.CAFETERIAS.keys():
        if cafe in user_text:
            target_cafeteria = cafe
            break

    # '급식' 명령어 처리 (키보드 호출)
    if "급식" in user_text and not target_cafeteria:
        names = list(config.CAFETERIAS.keys())
        keyboard = [names[i:i+2] for i in range(0, len(names), 2)]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("조회할 식당을 선택해주세요 (기본: 점심):", reply_markup=reply_markup)
        return

    # 식당 이름이 포함되어 있는 경우 메뉴 출력
    if target_cafeteria:
        is_dinner = "저녁" in user_text
        
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        today_idx = datetime.now().weekday()
        target_day = weekdays[today_idx]

        if today_idx >= 6:
            await update.message.reply_text("오늘은 일요일입니다. 주말엔 휴무입니다! 🍕")
            return

        cafeteria_data = current_menus.get(target_cafeteria, {})
        day_data = cafeteria_data.get(target_day, {})

        if day_data:
            # '저녁' 수식어 포함 여부에 따라 분기
            if is_dinner:
                meal_data = day_data.get('석식', '정보가 없습니다.')
                meal_title = "🌙 <b>[석식]</b>"
            else:
                meal_data = day_data.get('중식', '정보가 없습니다.')
                meal_title = "☀️ <b>[중식]</b>"
            
            # 단일 식단만 포함하도록 메시지 재구성
            msg = (
                f"🍴 <b>오늘({target_day}) [{target_cafeteria}] 식단</b>\n"
                f"━━━━━━━━━━━━━━\n\n"
                f"{meal_title}\n{meal_data}\n\n"
                f"━━━━━━━━━━━━━━"
            )
            
            await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"{target_cafeteria}의 {target_day}요일 식단 정보를 불러오지 못했습니다.")