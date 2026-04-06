from telegram import Update, ReplyKeyboardMarkup
<<<<<<< HEAD
=======
from telegram.constants import ParseMode 
>>>>>>> e67a6b0 (텔그봇 안내 로직 개선: 사용자 입력 처리 및 메뉴 출력 방식 수정)
from telegram.ext import ContextTypes
from datetime import datetime
import config

# 모든 식당의 데이터를 저장할 전역 변수 (복수형으로 통일)
current_menus = {}

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_text = update.message.text.strip()

<<<<<<< HEAD
    # 1. "급식" 입력 시 식당 선택 버튼 출력
    if "급식" in user_text and user_text not in config.CAFETERIAS:
=======
    # 입력된 텍스트에서 실제 식당 이름 추출
    target_cafeteria = None
    for cafe in config.CAFETERIAS.keys():
        if cafe in user_text:
            target_cafeteria = cafe
            break

    # '급식' 명령어 처리 (키보드 호출)
    if "급식" in user_text and not target_cafeteria:
>>>>>>> e67a6b0 (텔그봇 안내 로직 개선: 사용자 입력 처리 및 메뉴 출력 방식 수정)
        names = list(config.CAFETERIAS.keys())
        # 버튼을 2개씩 한 줄에 배치
        keyboard = [names[i:i+2] for i in range(0, len(names), 2)]
<<<<<<< HEAD
        
        reply_markup = ReplyKeyboardMarkup(
            keyboard, 
            one_time_keyboard=True, 
            resize_keyboard=True
        )
        
        await update.message.reply_text(
            "조회할 식당을 선택해주세요:", 
            reply_markup=reply_markup
        )
        return

    # 2. 식당 이름을 직접 클릭(입력)했을 때 식단 출력
    if user_text in config.CAFETERIAS:
=======
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("조회할 식당을 선택해주세요 (기본: 점심):", reply_markup=reply_markup)
        return

    # 식당 이름이 포함되어 있는 경우 메뉴 출력
    if target_cafeteria:
        is_dinner = "저녁" in user_text
        
>>>>>>> e67a6b0 (텔그봇 안내 로직 개선: 사용자 입력 처리 및 메뉴 출력 방식 수정)
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        today_idx = datetime.now().weekday()
        target_day = weekdays[today_idx]

        if today_idx >= 6: # 일요일
            await update.message.reply_text("오늘은 일요일입니다. 주말엔 휴무입니다! 🍕")
            return

<<<<<<< HEAD
        # 선택한 식당의 데이터 가져오기
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
=======
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
>>>>>>> e67a6b0 (텔그봇 안내 로직 개선: 사용자 입력 처리 및 메뉴 출력 방식 수정)
        else:
            await update.message.reply_text(f"{target_cafeteria}의 {target_day}요일 식단 정보를 불러오지 못했습니다.")