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

# 브라우저처럼 보이게 하기 위한 헤더 추가
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

weekly_menu = {}

def fetch_knu_menu():
    global weekly_menu
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    date_str = monday.strftime('%Y-%m-%d')
    
    url = f"{BASE_URL}&selDate={date_str}"
    print(f"[*] 접속 시도 URL: {url}") # 디버그용 로그
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        print(f"[*] 응답 상태 코드: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.select_one('.shop_table')
        
        if not table:
            print("[!] 오류: 식단 테이블(.shop_table)을 찾을 수 없습니다.")
            # 사이트 HTML 구조가 바뀌었는지 확인하기 위해 일부 출력
            print(f"[*] HTML 앞부분: {response.text[:200]}")
            return

        rows = table.select('tbody tr')
        print(f"[*] 찾은 데이터 행(row) 개수: {len(rows)}")
        
        new_menu = {}
        for row in rows:
            cols = row.select('td')
            if len(cols) >= 2:
                day_info = cols[0].get_text(strip=True)
                menu_content = cols[1].get_text("\n", strip=True)
                new_menu[day_info] = menu_content
                print(f"[*] 데이터 로드 성공: {day_info}")
        
        weekly_menu = new_menu
        print(f"[*] 총 {len(weekly_menu)}일치 식단 업데이트 완료")
    except Exception as e:
        print(f"[!] 크롤링 중 예외 발생: {e}")

async def send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # '급식' 혹은 '/급식'이라는 메시지가 왔을 때만 동작
    if update.message.text not in ['급식', '/급식']:
        return

    today_weekday = datetime.now().weekday()
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    target_day = weekdays[today_weekday]
    
    result = f"오늘({target_day}요일)의 식단 정보를 찾을 수 없습니다."
    
    if weekly_menu:
        for day, content in weekly_menu.items():
            if f"({target_day})" in day:
                result = f"🍴 {day} 식단:\n\n{content}"
                break
            
    await update.message.reply_text(result)

if __name__ == '__main__':
    fetch_knu_menu()
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_knu_menu, 'cron', day_of_week='mon', hour=9)
    scheduler.start()
    
    # 토큰 체크
    if not TELEGRAM_TOKEN:
        print("에러: TELEGRAM_TOKEN 환경 변수가 설정되지 않았습니다.")
        exit(1)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # CommandHandler('급식', ...) 대신 MessageHandler 사용 (한글 대응)
    # 사용자가 '급식' 또는 '/급식'을 입력하면 반응합니다.
    app.add_handler(MessageHandler(filters.TEXT & (filters.Regex('^급식$') | filters.Regex('^/급식$')), send_menu))
    
    print("봇이 정상 실행되었습니다.")
    app.run_polling()