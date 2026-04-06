import config
import handlers
from scraper import KnuScraper
# [수정됨] CommandHandler 추가 임포트
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import re

def update_menu_task():
    print(f"[*] {datetime.now()} 전체 식당 업데이트 시작")
    all_menus = KnuScraper.fetch_all_menus()
    if all_menus:
        handlers.current_menus = all_menus
        print(f"[*] {len(all_menus)}개 식당 데이터 업데이트 완료")
    else:
        print("[!] 식단 데이터를 가져오는 데 실패했습니다.")

if __name__ == '__main__':
    update_menu_task()
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_menu_task, 'cron', day_of_week='mon', hour=6, minute=0)
    scheduler.start()
    
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    
    # [새로 추가된 부분] /start 와 /help 명령어에 대해 start_handler를 연결합니다.
    app.add_handler(CommandHandler('start', handlers.start_handler))
    app.add_handler(CommandHandler('help', handlers.start_handler))
    
    # 공식 이름과 모든 별명을 통합
    all_valid_names = list(config.CAFETERIAS.keys())
    for aliases in config.CAFETERIA_ALIASES.values():
        all_valid_names.extend(aliases)
        
    cafeteria_names_str = '|'.join(all_valid_names)
    cafeteria_pattern = f"^(저녁\s*)?({cafeteria_names_str})$"
    
    cafeteria_filter = filters.TEXT & (filters.Regex('급식') | filters.Regex(cafeteria_pattern))
    
    app.add_handler(MessageHandler(cafeteria_filter, handlers.menu_handler))
    
    print("[*] 봇 가동 중... (명령어 대기)")
    app.run_polling()