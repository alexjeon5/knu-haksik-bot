import config
import handlers
from scraper import KnuScraper
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

def update_menu_task():
    print(f"[*] {datetime.now()} 전체 식당 업데이트 시작")
    all_menus = KnuScraper.fetch_all_menus()
    if all_menus:
        handlers.current_menus = all_menus # handlers의 변수 직접 갱신
        print(f"[*] {len(all_menus)}개 식당 데이터 업데이트 완료")

if __name__ == '__main__':
    update_menu_task() # 초기 실행 시 즉시 로드
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_menu_task, 'cron', day_of_week='mon', hour=6, minute=0)
    scheduler.start()
    
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    
    # '급식' 단어 또는 식당 이름에 반응
    cafeteria_filter = filters.TEXT & (filters.Regex('급식') | filters.In(config.CAFETERIAS.keys()))
    app.add_handler(MessageHandler(cafeteria_filter, handlers.menu_handler))
    
    print("[*] 봇 가동 중 (멀티 식당 지원 모드)")
    app.run_polling()