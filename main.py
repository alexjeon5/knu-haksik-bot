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
    # 초기 데이터 로드
    update_menu_task()
    
    # 스케줄러 (매주 월요일 오전 6시)
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_menu_task, 'cron', day_of_week='mon', hour=6, minute=0)
    scheduler.start()
    
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    
    # 식당 이름들을 포함하는 정규표현식 패턴 생성 ('저녁 ' 수식어를 선택적으로 허용)
    cafeteria_names = '|'.join(config.CAFETERIAS.keys())
    cafeteria_pattern = f"^(저녁\s*)?({cafeteria_names})$"
    
    # 필터 설정: '급식' 단어 포함 또는 정규식 패턴과 일치
    cafeteria_filter = filters.TEXT & (filters.Regex('급식') | filters.Regex(cafeteria_pattern))
    
    app.add_handler(MessageHandler(cafeteria_filter, handlers.menu_handler))
    
    print("[*] 봇 가동 중... (GUI 버튼 활성화)")
    app.run_polling()