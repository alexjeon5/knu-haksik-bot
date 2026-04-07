from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode 
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from bot import config, messages, utils

current_menus = {}
def get_inline_menu_keyboard(is_dinner=False, is_tomorrow=False, target_day=None):
    """
    is_tomorrow 여부에 따라 콜백 데이터에 'tomorrow_' 접두어를 추가합니다.
    """
    names = list(config.CAFETERIAS.keys())
    keyboard = []
    
    # 🌟 콜백 데이터 구조 설계: menu_[tomorrow_][dinner_]식당이름
    prefix = "menu_"
    if is_tomorrow: prefix += "tomorrow_"
    if is_dinner: prefix += "dinner_"
    
    available_cafeterias = []
    meal_type = '석식' if is_dinner else '중식'
    
    for name in names:
        if target_day:
            day_data = current_menus.get(name, {}).get(target_day, {})
            if meal_type not in day_data or not day_data.get(meal_type):
                continue 
        available_cafeterias.append(name)
        
    for i in range(0, len(available_cafeterias), 2):
        row = []
        for name in available_cafeterias[i:i+2]:
            row.append(InlineKeyboardButton(name, callback_data=f"{prefix}{name}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# /start 또는 /help 명령어 핸들러
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    today_idx = now.weekday()
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    
    # 주말이 아닐 경우에만 오늘 요일을 넘겨서 버튼 필터링
    target_day = weekdays[today_idx] if today_idx < 5 else None
    
    reply_markup = get_inline_menu_keyboard(is_dinner=False, target_day=target_day)
    await update.message.reply_text(
        messages.WELCOME_MSG, 
        parse_mode=ParseMode.HTML, 
        reply_markup=reply_markup
    )

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_text = update.message.text.strip().lstrip('/')
    
    # 🌟 [변경] 식당 이름/별칭 매칭을 config 함수로 단축
    target_cafeteria = config.find_cafeteria(user_text)

    # 🌟 [변경] 공통 유틸을 사용하여 날짜 정보 획득
    is_dinner = "저녁" in user_text
    is_tomorrow = "내일" in user_text
    date_info = utils.get_target_date_info(is_tomorrow)

    # 키워드 조합 처리 (학식/내일/저녁/점심)
    if not target_cafeteria and any(k in user_text for k in ["학식", "내일", "저녁", "점심"]):
        if not is_tomorrow and date_info["is_weekend"]:
            await update.message.reply_text("오늘은 주말 휴무입니다. '내일'을 입력해 월요일 식단을 확인하세요.")
            return

        reply_markup = get_inline_menu_keyboard(
            is_dinner=is_dinner, 
            is_tomorrow=is_tomorrow, 
            target_day=date_info["target_day"]
        )
        
        if not reply_markup.inline_keyboard:
            await update.message.reply_text(f"⚠️ {date_info['day_label']} {'저녁' if is_dinner else '점심'} 식단이 있는 식당이 없습니다.")
            return

        prompt = f"🍴 {date_info['day_label']} {'저녁' if is_dinner else '점심'} 식당을 선택하세요:"
        await update.message.reply_text(prompt, reply_markup=reply_markup)
        return

    # 식당이 지정된 경우
    if target_cafeteria:
        day_data = {}
        # 🌟 [변경] 다음 주 데이터 로드 로직 단순화
        if date_info["is_next_week"]:
            from bot.scraper import KnuScraper
            next_monday = date_info["now"] + timedelta(days=(7 - date_info["today_idx"]))
            next_week_data = KnuScraper.fetch_single_menu(config.CAFETERIAS[target_cafeteria], next_monday.strftime('%Y-%m-%d'))
            day_data = next_week_data.get('월', {}) if next_week_data else {}
        else:
            day_data = current_menus.get(target_cafeteria, {}).get(date_info["target_day"], {})

        if day_data:
            meal_type = '석식' if is_dinner else '중식'
            # 🌟 [변경] 메시지 포맷팅 함수 사용
            msg = utils.format_meal_message(
                date_info["day_label"], date_info["target_day"], 
                target_cafeteria, meal_type, day_data.get(meal_type, '정보가 없습니다.')
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"{target_cafeteria}의 {date_info['target_day']}요일 식단 정보를 불러오지 못했습니다.")

# 인라인 버튼 클릭 시 호출되는 콜백 핸들러
async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    is_tomorrow = "tomorrow_" in data
    is_dinner = "dinner_" in data
    target_cafeteria = data.replace("menu_", "").replace("tomorrow_", "").replace("dinner_", "")

    # 🌟 [변경] utils를 사용하여 날짜 정보 획득
    date_info = utils.get_target_date_info(is_tomorrow)

    if date_info["is_weekend"] and not is_tomorrow:
        await query.edit_message_text("오늘은 주말 휴무입니다. '내일' 식단을 확인하세요.")
        return

    day_data = {}
    if date_info["is_next_week"]:
        from bot.scraper import KnuScraper
        next_monday = date_info["now"] + timedelta(days=(7 - date_info["today_idx"]))
        next_week_data = KnuScraper.fetch_single_menu(config.CAFETERIAS[target_cafeteria], next_monday.strftime('%Y-%m-%d'))
        day_data = next_week_data.get('월', {}) if next_week_data else {}
    else:
        day_data = current_menus.get(target_cafeteria, {}).get(date_info["target_day"], {})

    if day_data:
        meal_type = '석식' if is_dinner else '중식'
        # 🌟 [변경] utils.format_meal_message를 사용하여 메시지 생성
        msg = utils.format_meal_message(
            date_info["day_label"], date_info["target_day"], 
            target_cafeteria, meal_type, day_data.get(meal_type, '정보가 없습니다.')
        )
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text(f"{target_cafeteria}의 {date_info['target_day']}요일 식단 정보를 불러오지 못했습니다.")