from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode 
from telegram.ext import ContextTypes
from datetime import datetime, timedelta  # timedelta 추가
from bot import config    # 수정됨
from bot import messages  # 수정됨

current_menus = {}

# /start 또는 /help 명령어 핸들러
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["급식"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        messages.WELCOME_MSG, 
        parse_mode=ParseMode.HTML, 
        reply_markup=reply_markup
    )

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_text = update.message.text.strip()

    target_cafeteria = None

    # 1. 식당 이름 및 별명 매칭 (기존 로직 유지)
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

    # '급식' 선택 버튼 처리
    if "급식" in user_text and not target_cafeteria:
        names = list(config.CAFETERIAS.keys())
        keyboard = [names[i:i+2] for i in range(0, len(names), 2)]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("조회할 식당을 선택해주세요 (기본: 점심):", reply_markup=reply_markup)
        return

    # 2. 식당이 지정된 경우 식단 데이터 가져오기
    if target_cafeteria:
        is_dinner = "저녁" in user_text
        is_tomorrow = "내일" in user_text
        
        now = datetime.now() 
        # now = datetime(2026, 3, 24, 12, 0) # 지정 날짜로 테스트
        today_idx = now.weekday()
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]

        day_data = {}
        day_label = ""
        target_day = ""

        # 상황별 데이터 조회 방식 분기
        if is_tomorrow and today_idx >= 4: # 금, 토, 일요일에 '내일'을 요청한 경우
            target_day = "월"
            day_label = "다음 주"
            
            # 다음 주 월요일 날짜 계산 및 실시간 크롤링
            next_monday = now + timedelta(days=(7 - today_idx))
            monday_str = next_monday.strftime('%Y-%m-%d')
            
            from bot.scraper import KnuScraper
            sqno = config.CAFETERIAS[target_cafeteria]
            next_week_data = KnuScraper.fetch_single_menu(sqno, monday_str)
            day_data = next_week_data.get('월', {}) if next_week_data else {}

        elif not is_tomorrow and today_idx >= 5: # 토, 일요일에 '오늘' 식단을 요청한 경우
            await update.message.reply_text("오늘은 주말입니다. 주말엔 휴무입니다! 🍕\n\"내일 + 식당 이름\"을 입력해 다음주 월요일 식단을 확인하세요.")
            return

        else: # 평일이거나 이번 주 내의 내일 식단인 경우 (메모리 캐시 사용)
            target_idx = today_idx + 1 if is_tomorrow else today_idx
            target_day = weekdays[target_idx]
            day_label = "내일" if is_tomorrow else "오늘"
            
            cafeteria_data = current_menus.get(target_cafeteria, {})
            day_data = cafeteria_data.get(target_day, {})

        # 3. 최종 메시지 구성 및 전송
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