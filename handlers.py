from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime

# 데이터 저장용 전역 변수 (main에서 업데이트)
current_menu = {}

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    today_idx = datetime.now().weekday()
    target_day = weekdays[today_idx]
    
    if today_idx >= 5:
        await update.message.reply_text(f"오늘은 {target_day}요일! 주말엔 맛있는 거 드세요! 🍕")
        return

    if target_day in current_menu:
        menu = current_menu[target_day]
        await update.message.reply_text(f"🍴 오늘({target_day})의 식단입니다:\n\n{menu}")
    else:
        await update.message.reply_text("식단 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")