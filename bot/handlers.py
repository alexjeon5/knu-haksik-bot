# bot/handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode 
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from bot import config, messages, utils

# 전역 변수로 관리되는 현재 주간 식단 데이터 저장소
current_menus = {}

def get_inline_menu_keyboard(is_dinner=False, is_tomorrow=False, target_day=None):
    """
    식당 선택을 위한 인라인 버튼 키보드를 생성하는 함수입니다.
    내일 여부와 식사 종류에 따라 콜백 데이터를 구성하며, 식단 데이터가 있는 식당만 표시합니다.
    """
    names = list(config.CAFETERIAS.keys())
    keyboard = []
    
    # 콜백 데이터 접두어 설정
    prefix = "menu_"
    if is_tomorrow: prefix += "tomorrow_"
    if is_dinner: prefix += "dinner_"
    
    available_cafeterias = []
    meal_type = '석식' if is_dinner else '중식'
    
    # 식단 데이터 존재 여부 확인 및 필터링
    for name in names:
        if target_day:
            day_data = current_menus.get(name, {}).get(target_day, {})
            if meal_type not in day_data or not day_data.get(meal_type):
                continue 
        available_cafeterias.append(name)
        
    # 버튼을 2열로 배치
    for i in range(0, len(available_cafeterias), 2):
        row = []
        for name in available_cafeterias[i:i+2]:
            row.append(InlineKeyboardButton(name, callback_data=f"{prefix}{name}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start 또는 /help 명령어 입력 시 초기 메뉴를 안내하는 핸들러입니다.
    """
    now = datetime.now()
    today_idx = now.weekday()
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    
    # 주말이 아닐 경우에만 오늘 요일을 버튼 필터링에 사용
    target_day = weekdays[today_idx] if today_idx < 5 else None
    
    reply_markup = get_inline_menu_keyboard(is_dinner=False, target_day=target_day)
    await update.message.reply_text(
        messages.WELCOME_MSG, 
        parse_mode=ParseMode.HTML, 
        reply_markup=reply_markup
    )

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    사용자가 직접 텍스트로 보낸 식단 요청을 처리하는 핸들러입니다.
    키워드 조합(내일/점심/저녁) 및 식당 이름을 분석하여 결과를 전송합니다.
    """
    if not update.message or not update.message.text: return
    user_text = update.message.text.strip().lstrip('/')
    
    # 입력된 텍스트에서 식당 식별
    target_cafeteria = config.find_cafeteria(user_text)

    # 요청 날짜 및 시간대 판별
    is_dinner = "저녁" in user_text
    is_tomorrow = "내일" in user_text
    date_info = utils.get_target_date_info(is_tomorrow)

    # 식당 없이 키워드만 입력된 경우 선택 버튼 출력
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
            await update.message.reply_text(f"{date_info['day_label']} {'저녁' if is_dinner else '점심'} 식단이 있는 식당이 없습니다.")
            return

        prompt = f"{date_info['day_label']} {'저녁' if is_dinner else '점심'} 식당을 선택하세요:"
        await update.message.reply_text(prompt, reply_markup=reply_markup)
        return

    # 식당이 확인된 경우 식단 메시지 전송
    if target_cafeteria:
        day_data = {}
        if date_info["is_next_week"]:
            # 다음 주 데이터가 필요한 경우 실시간으로 크롤링 수행
            from bot.scraper import KnuScraper
            next_monday = date_info["now"] + timedelta(days=(7 - date_info["today_idx"]))
            next_week_data = KnuScraper.fetch_single_menu(config.CAFETERIAS[target_cafeteria], next_monday.strftime('%Y-%m-%d'))
            day_data = next_week_data.get('월', {}) if next_week_data else {}
        else:
            day_data = current_menus.get(target_cafeteria, {}).get(date_info["target_day"], {})

        if day_data:
            meal_type = '석식' if is_dinner else '중식'
            msg = utils.format_meal_message(
                date_info["day_label"], date_info["target_day"], 
                target_cafeteria, meal_type, day_data.get(meal_type, '정보가 없습니다.')
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"{target_cafeteria}의 {date_info['target_day']}요일 식단 정보를 불러오지 못했습니다.")

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    사용자가 인라인 버튼을 클릭했을 때 호출되는 콜백 처리 핸들러입니다.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    # 콜백 데이터로부터 옵션 추출
    is_tomorrow = "tomorrow_" in data
    is_dinner = "dinner_" in data
    target_cafeteria = data.replace("menu_", "").replace("tomorrow_", "").replace("dinner_", "")

    # 날짜 정보 계산
    date_info = utils.get_target_date_info(is_tomorrow)

    # 주말 예외 처리
    if date_info["is_weekend"] and not is_tomorrow:
        await query.edit_message_text("오늘은 주말 휴무입니다. '내일' 식단을 확인하세요.")
        return

    day_data = {}
    if date_info["is_next_week"]:
        # 다음 주 월요일 데이터 실시간 조회
        from bot.scraper import KnuScraper
        next_monday = date_info["now"] + timedelta(days=(7 - date_info["today_idx"]))
        next_week_data = KnuScraper.fetch_single_menu(config.CAFETERIAS[target_cafeteria], next_monday.strftime('%Y-%m-%d'))
        day_data = next_week_data.get('월', {}) if next_week_data else {}
    else:
        day_data = current_menus.get(target_cafeteria, {}).get(date_info["target_day"], {})

    if day_data:
        meal_type = '석식' if is_dinner else '중식'
        msg = utils.format_meal_message(
            date_info["day_label"], date_info["target_day"], 
            target_cafeteria, meal_type, day_data.get(meal_type, '정보가 없습니다.')
        )
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text(f"{target_cafeteria}의 {date_info['target_day']}요일 식단 정보를 불러오지 못했습니다.")