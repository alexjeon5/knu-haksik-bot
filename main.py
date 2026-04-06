import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
BASE_URL = "https://coop.knu.ac.kr/sub03/sub01_01.html?shop_sqno=85"

weekly_menu = {}

def fetch_knu_menu():
    global weekly_menu
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    date_str = monday.strftime('%Y-%m-%d')
    
    try:
        response = requests.get(f"{BASE_URL}&selDate={date_str}")
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.select_one('.shop_table')
        rows = table.select('tbody tr')
        
        new_menu = {}
        for row in rows:
            cols = row.select('td')
            if len(cols) >= 2:
                day_info = cols[0].get_text(strip=True)
                menu_content = cols[1].get_text("\n", strip=True)
                new_menu[day_info] = menu_content
        weekly_menu = new_menu
        print(f"Update Success: {datetime.now()}")
    except Exception as e:
        print(f"Error: {e}")

async def send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today_weekday = datetime.now().weekday()
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    target_day = weekdays[today_weekday]
    
    result = "오늘의 식단 정보를 찾을 수 없습니다."
    for day, content in weekly_menu.items():
        if f"({target_day})" in day:
            result = f"🍴 {day} 식단:\n\n{content}"
            break
    await update.message.reply_text(result)

if __name__ == '__main__':
    fetch_knu_menu() # 시작 시 즉시 실행
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_knu_menu, 'cron', day_of_week='mon', hour=9)
    scheduler.start()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('급식', send_menu))
    app.run_polling()