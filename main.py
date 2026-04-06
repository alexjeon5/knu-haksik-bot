import config
import handlers
from scraper import KnuScraper
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import re # 정규표현식 모듈 추가

def update_menu_task():
    print(f"[*] {datetime.now()} 전체 식당 업데이트 시작")
    all_menus = KnuScraper.fetch_all_menus()
    if all_menus:
        handlers.current_menus = all_menus
        print(f"[*] {len(all_menus)}개 식당 데이터 업데이트 완료")

if __name__ == '__main__':
    # 1. 초기 데이터 로드
    update_menu_task()
    
    # 2. 스케줄러 설정 (매주 월요일 오전 6시)
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_menu_task, 'cron', day_of_week='mon', hour=6, minute=0)
    scheduler.start()
    
    # 3. 봇 실행
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    
    # [수정된 부분] 식당 이름들을 정규표현식 패턴으로 변환 (예: "^(정보센터식당|복지관 교직원식당|...)$")
    cafeteria_names_pattern = f"^({'|'.join(config.CAFETERIAS.keys())})$"
    
    # '급식' 단어 또는 등록된 식당 이름과 정확히 일치하는 메시지 필터링
    cafeteria_filter = filters.TEXT & (filters.Regex('급식') | filters.Regex(cafeteria_names_pattern))
    
    app.add_handler(MessageHandler(cafeteria_filter, handlers.menu_handler))
    
    print("[*] 봇 서버 가동 중 (멀티 식당 지원 완료)")
    app.run_polling()