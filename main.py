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
# 복지관 식당(shop_sqno=85) URL
BASE_URL = "https://coop.knu.ac.kr/sub03/sub01_01.html?shop_sqno=85"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

weekly_menu = {}

def fetch_knu_menu():
    global weekly_menu
    today = datetime.now()
    # 이번 주 월요일 날짜 계산
    monday = today - timedelta(days=today.weekday())
    date_str = monday.strftime('%Y-%m-%d')
    
    url = f"{BASE_URL}&selDate={date_str}"
    print(f"[*] 접속 시도 URL: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8' # 한글 깨짐 방지
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 방법 1: .shop_table 클래스 안의 table 찾기
        table = soup.select_one('.shop_table table')
        
        # 방법 2: 방법 1이 실패하면 페이지 내 첫 번째 table 태그 찾기
        if not table:
            table = soup.find('table')

        if not table:
            print("[!] 오류: 페이지 내에서 어떠한 테이블도 찾을 수 없습니다.")
            return

        # tbody 안의 모든 행(tr) 가져오기
        rows = table.find_all('tr')
        print(f"[*] 찾은 데이터 행(row) 개수: {len(rows)}")
        
        new_menu = {}
        for row in rows:
            cols = row.find_all(['th', 'td']) # 날짜는 th일 수도 있고 td일 수도 있음
            if len(cols) >= 2:
                day_info = cols[0].get_text(strip=True)
                # 요일 정보가 포함된 행인지 확인 (예: 월, 화, 수...)
                if any(day in day_info for day in ['월', '화', '수', '목', '금', '토', '일']):
                    menu_content = cols[1].get_text("\n", strip=True)
                    new_menu[day_info] = menu_content
                    print(f"[*] 데이터 로드 성공: {day_info}")
        
        if not new_menu:
            print("[!] 오류: 테이블은 찾았으나 유효한 식단 데이터를 추출하지 못했습니다.")
            return

        weekly_menu = new_menu
        print(f"[*] 총 {len(weekly_menu)}일치 식단 업데이트 완료")
        
    except Exception as e:
        print(f"[!] 크롤링 중 예외 발생: {e}")

async def send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # '급식' 또는 '/급식' 텍스트 감지
    text = update.message.text
    if '급식' not in text:
        return

    today_weekday = datetime.now().weekday()
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    target_day = weekdays[today_weekday]
    
    print(f"[*] 사용자 요청 수신: {target_day}요일 식단 요청")
    
    result = f"오늘({target_day}요일)의 식단 정보를 찾을 수 없습니다.\n아직 식단이 등록되지 않았거나 주말일 수 있습니다."
    
    if weekly_menu:
        for day, content in weekly_menu.items():
            if f"({target_day})" in day or target_day in day:
                if content.strip(): # 내용이 비어있지 않은지 확인
                    result = f"🍴 {day} 식단:\n\n{content}"
                else:
                    result = f"🍴 {day} 식단:\n\n등록된 식단 메뉴가 없습니다."
                break
            
    await update.message.reply_text(result)

if __name__ == '__main__':
    fetch_knu_menu()
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_knu_menu, 'cron', day_of_week='mon', hour=9)
    scheduler.start()
    
    if not TELEGRAM_TOKEN:
        print("에러: TELEGRAM_TOKEN 환경 변수가 설정되지 않았습니다.")
        exit(1)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    # 정규표현식으로 '급식'이 포함된 모든 메시지에 반응
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('급식'), send_menu))
    
    print("봇이 정상 실행되었습니다.")
    app.run_polling()