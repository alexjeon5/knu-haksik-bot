from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode 
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from bot import config
from bot import messages

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
    target_cafeteria = None

    # 1. 식당 이름 및 별명 매칭
    for cafe in config.CAFETERIAS.keys():
        if cafe in user_text:
            target_cafeteria = cafe
            break

    if not target_cafeteria:
        for official_name, aliases in config.CAFETERIA_ALIASES.items():
            for alias in aliases:
                if alias in user_text:
                    target_cafeteria = official_name
                    break
            if target_cafeteria:
                break

   # 🌟 '학식/내일/저녁' 키워드 조합 처리
    if not target_cafeteria and any(k in user_text for k in ["학식", "내일", "저녁", "점심"]):
        is_dinner = "저녁" in user_text
        is_tomorrow = "내일" in user_text
        
        now = datetime.now()
        today_idx = now.weekday()
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        
        # 날짜 계산 (금요일에 '내일' 입력 시 다음주 월요일 처리 포함)
        if is_tomorrow:
            if today_idx >= 4: # 금, 토, 일
                target_day = "월"
                day_label = "다음 주 월요일"
            else:
                target_day = weekdays[today_idx + 1]
                day_label = "내일"
        else:
            if today_idx >= 5: # 토, 일
                await update.message.reply_text("오늘은 주말 휴무입니다. '내일'을 입력해 월요일 식단을 확인하세요.")
                return
            target_day = weekdays[today_idx]
            day_label = "오늘"

        reply_markup = get_inline_menu_keyboard(is_dinner=is_dinner, is_tomorrow=is_tomorrow, target_day=target_day)
        
        if not reply_markup.inline_keyboard:
            await update.message.reply_text(f"⚠️ {day_label} {'저녁' if is_dinner else '점심'} 식단이 있는 식당이 없습니다.")
            return

        prompt = f"🍴 {day_label} {'저녁' if is_dinner else '점심'} 식당을 선택하세요:"
        await update.message.reply_text(prompt, reply_markup=reply_markup)
        return

    # 2. 식당이 지정된 경우 (텍스트 직접 입력 시)
    if target_cafeteria:
        is_dinner = "저녁" in user_text
        is_tomorrow = "내일" in user_text
        
        now = datetime.now() 
        today_idx = now.weekday()
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]

        day_data = {}
        day_label = ""
        target_day = ""

        if is_tomorrow and today_idx >= 4:
            target_day = "월"
            day_label = "다음 주"
            next_monday = now + timedelta(days=(7 - today_idx))
            monday_str = next_monday.strftime('%Y-%m-%d')
            
            from bot.scraper import KnuScraper
            sqno = config.CAFETERIAS[target_cafeteria]
            next_week_data = KnuScraper.fetch_single_menu(sqno, monday_str)
            day_data = next_week_data.get('월', {}) if next_week_data else {}

        elif not is_tomorrow and today_idx >= 5:
            await update.message.reply_text("오늘은 주말입니다. 주말엔 휴무입니다! 🍕\n\"내일 + 식당 이름\"을 입력해 다음주 월요일 식단을 확인하세요.")
            return

        else:
            target_idx = today_idx + 1 if is_tomorrow else today_idx
            target_day = weekdays[target_idx]
            day_label = "내일" if is_tomorrow else "오늘"
            
            cafeteria_data = current_menus.get(target_cafeteria, {})
            day_data = cafeteria_data.get(target_day, {})

        if day_data:
            meal_type = '석식' if is_dinner else '중식'
            meal_title = "🌙 <b>[석식]</b>" if is_dinner else "☀️ <b>[중식]</b>"
            meal_content = day_data.get(meal_type, '정보가 없습니다.')
            
            msg = (
                f"🍴 <b>{day_label}({target_day}) [{target_cafeteria}] 식단</b>\n"
                f"━━━━━━━━━━━━━━\n\n"
                f"{meal_title}\n{meal_content}\n\n"
                f"━━━━━━━━━━━━━━"
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"{target_cafeteria}의 {target_day}요일 식단 정보를 불러오지 못했습니다.")

# 인라인 버튼 클릭 시 호출되는 콜백 핸들러
async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    is_tomorrow = "tomorrow_" in data
    is_dinner = "dinner_" in data
    target_cafeteria = data.replace("menu_", "").replace("tomorrow_", "").replace("dinner_", "")

    now = datetime.now()
    today_idx = now.weekday()
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]

    day_data = {}
    day_label = "오늘"
    target_day = weekdays[today_idx]

    # 날짜 및 데이터 로드 로직 (menu_handler의 로직과 동기화)
    if is_tomorrow:
        if today_idx >= 4: # 금, 토, 일
            target_day = "월"
            day_label = "다음 주"
            # 다음 주 월요일 데이터 크롤링 (current_menus에 없을 경우 대비)
            from bot.scraper import KnuScraper
            next_monday = now + timedelta(days=(7 - today_idx))
            monday_str = next_monday.strftime('%Y-%m-%d')
            next_week_data = KnuScraper.fetch_single_menu(config.CAFETERIAS[target_cafeteria], monday_str)
            day_data = next_week_data.get('월', {}) if next_week_data else {}
        else:
            target_day = weekdays[today_idx + 1]
            day_label = "내일"
            day_data = current_menus.get(target_cafeteria, {}).get(target_day, {})
    else:
        if today_idx >= 5: # 주말 예외 처리
            await query.edit_message_text("오늘은 주말 휴무입니다. '내일' 식단을 확인하세요.")
            return
        day_data = current_menus.get(target_cafeteria, {}).get(target_day, {})

    if day_data:
        meal_type = '석식' if is_dinner else '중식'
        meal_title = "🌙 <b>[석식]</b>" if is_dinner else "☀️ <b>[중식]</b>"
        meal_content = day_data.get(meal_type, '정보가 없습니다.')
        
        msg = (
            f"🍴 <b>{day_label}({target_day}) [{target_cafeteria}] 식단</b>\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"{meal_title}\n{meal_content}\n\n"
            f"━━━━━━━━━━━━━━"
        )
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text(f"{target_cafeteria}의 {target_day}요일 식단 정보를 불러오지 못했습니다.")