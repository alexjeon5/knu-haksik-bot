# bot/utils.py
from datetime import datetime, timedelta
from bot import config

def get_target_date_info(is_tomorrow=False):
    """
    현재 시간을 기준으로 조회 대상 요일과 라벨을 반환합니다.
    금요일에 '내일' 조회 시 다음 주 월요일로 처리하는 로직을 포함합니다.
    """
    now = datetime.now()
    today_idx = now.weekday()
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    
    day_label = "오늘"
    target_day = weekdays[today_idx]
    is_weekend = today_idx >= 5
    is_next_week = False
    
    if is_tomorrow:
        if today_idx >= 4:  # 금, 토, 일
            target_day = "월"
            day_label = "다음 주"
            is_next_week = True
        else:
            target_day = weekdays[today_idx + 1]
            day_label = "내일"
    
    return {
        "target_day": target_day,
        "day_label": day_label,
        "is_weekend": is_weekend,
        "is_next_week": is_next_week,
        "now": now,
        "today_idx": today_idx
    }

def format_meal_message(day_label, day_str, cafe_name, meal_type, content):
    """식단 메시지 형식을 통일합니다."""
    meal_title = "🌙 <b>[석식]</b>" if meal_type == '석식' else "☀️ <b>[중식]</b>"
    return (
        f"🍴 <b>{day_label}({day_str}) [{cafe_name}] 식단</b>\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"{meal_title}\n{content}\n\n"
        f"━━━━━━━━━━━━━━"
    )