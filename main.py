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
# 공학관 교직원 식당 (외부업체)
BASE_URL = "https://coop.knu.ac.kr/sub03/sub01_01.html?shop_sqno=85"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 주간 식단을 저장할 전역 변수
weekly_menu = {}

def fetch_knu_menu():
    global weekly_menu
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    date_str = monday.strftime('%Y-%m-%d')
    
    url = f"{BASE_URL}&selDate={date_str}"
    print(f"[*] 접속 시도 URL: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 식단 테이블 찾기
        table = soup.select_one('.shop_table table') or soup.select_one('.shop_table')
        if not table:
            print("[!] 오류: 식단 테이블을 찾을 수 없습니다.")
            return

        rows = table.find_all('tr')
        if len(rows) < 2:
            print("[!] 오류: 식단 데이터 행이 부족합니다.")
            return

        # 1. 첫 번째 행(헤더)에서 요일별 인덱스 파악
        header_cols = rows[0].find_all(['th', 'td'])
        day_indices = {} # {"월": 1, "화": 2, ...}
        
        for idx, col in enumerate(header_cols):
            text = col.get_text(strip=True)
            for day in ['월', '화', '수', '목', '금']:
                if day in text:
                    day_indices[day] = idx
        
        # 2. 두 번째 행(데이터)에서 식단 추출
        # 공학관 식당은 보통 중식(정식) 한 줄만 있음
        data_cols = rows[1].find_all(['th', 'td'])
        
        new_menu = {}
        for day, idx in day_indices.items():
            if idx < len(data_cols):
                # <br/> 태그를 줄바꿈으로 변환하여 추출
                menu_text = data_cols[idx].get_text("\n", strip=True)
                new_menu[day] = menu_text
                print(f"[*] {day}요일 식단 로드 완료")

        if not new_menu:
            print("[!] 오류: 추출된 식단이 없습니다.")
            return

        weekly_menu = new_menu
        print(f"[*] 총 {len(weekly_menu)}일치 식단 업데이트 완료")
        
    except Exception as e:
        print(f"[!] 에러 발생: {e}")

async def send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # '급식' 단어가 포함된 메시지 처리
    if not update.message or not update.message.text: return
    if '급식' not in update.message.text: return

    # 현재 요일 확인
    today_weekday = datetime.now().weekday()
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    target_day = weekdays[today_weekday]
    
    print(f"[*] 사용자 요청: {target_day}요일 식단")
    
    # 주말 예외 처리
    if today_weekday >= 5:
        await update.message.reply_text("오늘은 주말입니다. 식단이 없습니다! 😎")
        return

    if target_day in weekly_menu:
        content = weekly_menu[target_day]
        # '정식'이라는 글자 뒤에 실제 메뉴가 오도록 가독성 조절
        response_text = f"🍴 오늘({target_day})의 공학관 식단:\n\n{content}"
    else:
        response_text = f"오늘({target_day}) 식단 정보를 가져오지 못했습니다. 사이트를 확인해 주세요."
            
    await update.message.reply_text(response_text)

if __name__ == '__main__':
    fetch_knu_menu()
    
    scheduler = BackgroundScheduler()
    # 매주 월요일 오전 9시에 갱신
    scheduler.add_job(fetch_knu_menu, 'cron', day_of_week='mon', hour=9)
    scheduler.start()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    # 모든 텍스트 메시지 중 '급식' 포함 시 반응
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('급식'), send_menu))
    
    print("봇이 정상 실행되었습니다. 텔레그램에서 '급식'을 입력해 보세요.")
    app.run_polling()