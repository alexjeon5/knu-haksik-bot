import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
# 공학관 교직원식당 URL
BASE_URL = "https://coop.knu.ac.kr/sub03/sub01_01.html?shop_sqno=85"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

weekly_menu = {}

def fetch_knu_menu():
    global weekly_menu
    today = datetime.now()
    # 이번 주 월요일 날짜 계산
    monday = today - timedelta(days=today.weekday())
    date_str = monday.strftime('%Y-%m-%d')
    
    url = f"{BASE_URL}&selDate={date_str}"
    print(f"[*] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 식단 업데이트 시작: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tables = soup.find_all('table')
        target_table = None
        for t in tables:
            t_text = t.get_text()
            if '월' in t_text and ('분류' in t_text or '중식' in t_text):
                target_table = t
                break
        
        if not target_table:
            print("[!] 오류: 식단표 테이블을 찾을 수 없습니다.")
            return

        rows = target_table.find_all('tr')
        header_cols = rows[0].find_all(['th', 'td'])
        day_indices = {}
        for idx, col in enumerate(header_cols):
            txt = col.get_text(strip=True)
            for d in ['월', '화', '수', '목', '금']:
                if d in txt:
                    day_indices[d] = idx
        
        new_menu = {}
        for r in rows[1:]:
            cols = r.find_all(['th', 'td'])
            for day, idx in day_indices.items():
                if idx < len(cols):
                    menu_text = cols[idx].get_text("\n", strip=True)
                    if day in new_menu:
                        new_menu[day] += "\n\n" + menu_text
                    else:
                        new_menu[day] = menu_text
        
        if not new_menu:
            print("[!] 오류: 유효한 식단 데이터를 찾지 못했습니다.")
            return

        weekly_menu = new_menu
        print(f"[*] 업데이트 완료! (로드된 요일: {', '.join(weekly_menu.keys())})")
        
    except Exception as e:
        print(f"[!] 업데이트 중 예외 발생: {e}")

async def send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    if '급식' not in update.message.text: return

    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    today_idx = datetime.now().weekday()
    target_day = weekdays[today_idx]
    
    if today_idx >= 5:
        await update.message.reply_text(f"오늘은 {target_day}요일입니다. 주말에는 식단이 없어요! 🏖️")
        return

    if target_day in weekly_menu:
        menu = weekly_menu[target_day]
        await update.message.reply_text(f"🍴 오늘({target_day})의 공학관 식단입니다:\n\n{menu}")
    else:
        await update.message.reply_text(f"오늘({target_day}) 식단 정보를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.")

if __name__ == '__main__':
    # [설정 1] 봇 시작 시 즉시 식단 데이터를 불러옴
    print("[*] 시스템 시작: 초기 식단 데이터를 불러옵니다...")
    fetch_knu_menu()
    
    # [설정 2] 스케줄러 설정: 매주 월요일 오전 6시 0분
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_knu_menu, 'cron', day_of_week='mon', hour=6, minute=0)
    scheduler.start()
    print("[*] 스케줄러 등록 완료: 매주 월요일 오전 6시에 업데이트됩니다.")
    
    if not TELEGRAM_TOKEN:
        print("[!] 에러: TELEGRAM_TOKEN 환경 변수가 없습니다.")
        exit(1)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('급식'), send_menu))
    
    print("[*] 텔레그램 봇 폴링 시작...")
    app.run_polling()