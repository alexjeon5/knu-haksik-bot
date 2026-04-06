import config
import handlers
from scraper import KnuScraper
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

def update_menu_task():
    print(f"[*] {datetime.now()} 스케줄 작업 시작")
    menu_data = KnuScraper.fetch_weekly_menu()
    if menu_data:
        handlers.current_menu = menu_data
        print("[*] 메뉴 데이터 업데이트 완료")

if __name__ == '__main__':
    # 1. 초기 데이터 로드
    update_menu_task()
    
    # 2. 스케줄러 설정
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_menu_task, 'cron', day_of_week='mon', hour=6)
    scheduler.start()
    
    # 3. 봇 실행
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('급식'), handlers.menu_handler))
    
    print("[*] 봇 서버 가동 중...")
    app.run_polling()