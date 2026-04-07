from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode 
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from bot import config
from bot import messages

current_menus = {}

def get_inline_menu_keyboard(is_dinner=False):
    """
    식당 목록 인라인 버튼 생성. 
    is_dinner가 True면 버튼 클릭 시 저녁 식단이 조회되도록 설정합니다.
    """
    names = list(config.CAFETERIAS.keys())
    keyboard = []
    # 🌟 저녁 여부에 따라 콜백 데이터의 머리말(prefix)을 다르게 설정합니다.
    prefix = "dinner_menu_" if is_dinner else "menu_"
    
    for i in range(0, len(names), 2):
        row = []
        for name in names[i:i+2]:
            row.append(InlineKeyboardButton(name, callback_data=f"{prefix}{name}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# /start 또는 /help 명령어 핸들러
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = get_inline_menu_keyboard()
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

    # 🌟 '학식' 선택 버튼 처리 (점심/저녁 자동 판별)
    if "학식" in user_text and not target_cafeteria:
        is_dinner = "저녁" in user_text
        reply_markup = get_inline_menu_keyboard(is_dinner=is_dinner)
        
        prompt = "🌙 조회할 식당을 선택해주세요 (오늘 저녁):" if is_dinner else "☀️ 조회할 식당을 선택해주세요 (오늘 점심):"
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

    # 🌟 클릭한 버튼의 prefix를 통해 저녁 조회 여부를 확인합니다.
    is_dinner = data.startswith("dinner_menu_")
    prefix = "dinner_menu_" if is_dinner else "menu_"
    target_cafeteria = data.replace(prefix, "")

    now = datetime.now()
    today_idx = now.weekday()
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]

    if today_idx >= 5:
        await query.edit_message_text("오늘은 주말입니다. 주말엔 휴무입니다! 🍕\n\"내일 + 식당 이름\"을 입력해 다음주 월요일 식단을 확인하세요.")
        return

    target_day = weekdays[today_idx]
    cafeteria_data = current_menus.get(target_cafeteria, {})
    day_data = cafeteria_data.get(target_day, {})

    if day_data:
        # 🌟 판별된 is_dinner에 따라 중식/석식을 가져옵니다.
        meal_type = '석식' if is_dinner else '중식'
        meal_title = "🌙 <b>[석식]</b>" if is_dinner else "☀️ <b>[중식]</b>"
        meal_content = day_data.get(meal_type, '정보가 없습니다.')
        
        msg = (
            f"🍴 <b>오늘({target_day}) [{target_cafeteria}] 식단</b>\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"{meal_title}\n{meal_content}\n\n"
            f"━━━━━━━━━━━━━━"
        )
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text(f"{target_cafeteria}의 {target_day}요일 식단 정보를 불러오지 못했습니다.")