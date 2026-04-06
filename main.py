import config
import handlers
from scraper import KnuScraper
from telegram.ext import ApplicationBuilder, MessageHandler, filters
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
    
    # [수정됨] 공식 이름과 모든 별명을 하나의 리스트로 통합
    all_valid_names = list(config.CAFETERIAS.keys())
    for aliases in config.CAFETERIA_ALIASES.values():
        all_valid_names.extend(aliases)
        
    # [수정됨] 식당 이름(공식 명칭 + 별명)들을 모두 모아 정규표현식 패턴 생성
    cafeteria_names_str = '|'.join(all_valid_names)
    cafeteria_pattern = f"^(저녁\s*)?({cafeteria_names_str})$"
    
    # 필터 설정: '급식' 단어 포함 또는 정규식 패턴과 일치
    cafeteria_filter = filters.TEXT & (filters.Regex('급식') | filters.Regex(cafeteria_pattern))
    
    app.add_handler(MessageHandler(cafeteria_filter, handlers.menu_handler))
    
    print("[*] 봇 가동 중... (GUI 버튼 활성화)")
    app.run_polling()