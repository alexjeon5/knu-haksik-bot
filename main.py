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
BASE_URL = "https://coop.knu.ac.kr/sub03/sub01_01.html?shop_sqno=85"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

# { '월': {'중식': '...', '석식': '...'}, '화': { ... } } 구조로 저장
weekly_menu = {}

def fetch_knu_menu():
    global weekly_menu
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    date_str = monday.strftime('%Y-%m-%d')
    
    url = f"{BASE_URL}&selDate={date_str}"
    print(f"[*] [{datetime.now().strftime('%H:%M:%S')}] 데이터 업데이트 시도: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        new_menu = {day: {} for day in ['월', '화', '수', '목', '금', '토']}
        
        # '중식', '석식' 섹션을 각각 찾음
        sections = soup.select('div.week_table')
        
        for section in sections:
            # 섹션 제목 (중식 또는 석식)
            title_tag = section.select_one('p.title')
            if not title_tag: continue
            category = title_tag.get_text(strip=True) # "중식" 또는 "석식"
            
            # 해당 테이블의 모든 td(요일별 식단) 추출
            tds = section.select('tbody tr td')
            days = ['월', '화', '수', '목', '금', '토']
            
            for i, td in enumerate(tds):
                if i < len(days):
                    # 식단 내용이 들어있는 <p> 태그 추출
                    menu_p = td.select_one('li.first p')
                    if menu_p:
                        # <br/>을 줄바꿈으로 변환하여 텍스트 추출
                        menu_text = menu_p.get_text("\n", strip=True)
                        new_menu[days[i]][category] = menu_text

        if not any(new_menu.values()):
            print("[!] 오류: 식단 데이터를 찾지 못했습니다.")
            return

        weekly_menu = new_menu
        print(f"[*] 업데이트 성공! (중식/석식 데이터 로드 완료)")
        
    except Exception as e:
        print(f"[!] 에러 발생: {e}")

async def send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    if '급식' not in update.message.text: return

    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    today_idx = datetime.now().weekday()
    target_day = weekdays[today_idx]
    
    if today_idx >= 6: # 일요일 예외 처리
        await update.message.reply_text("오늘은 일요일입니다. 식단이 없습니다! 🏖️")
        return

    if target_day in weekly_menu and weekly_menu[target_day]:
        day_data = weekly_menu[target_day]
        lunch = day_data.get('중식', '등록된 정보가 없습니다.')
        dinner = day_data.get('석식', '등록된 정보가 없습니다.')
        
        msg = (
            f"🍴 오늘({target_day}요일)의 공학관 식단\n"
            f"━━━━━━━━━━━━━━\n"
            f"☀️ [중식]\n{lunch}\n\n"
            f"🌙 [석식]\n{dinner}\n"
            f"━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text(f"오늘({target_day}) 식단 정보를 가져오지 못했습니다. 아직 등록 전일 수 있습니다.")

if __name__ == '__main__':
    # 시작 시 즉시 실행
    fetch_knu_menu()
    
    # 매주 월요일 오전 6시 실행
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_knu_menu, 'cron', day_of_week='mon', hour=6, minute=0)
    scheduler.start()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('급식'), send_menu))
    
    print("[*] 봇 가동 시작 (월요일 06:00 업데이트)")
    app.run_polling()