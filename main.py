# main.py
from bot import config, handlers
from bot.reservation import get_conv_handler, restore_reservations
from bot.scraper import KnuScraper
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import re

def update_menu_task():
    """전체 식당의 주간 식단 데이터를 크롤링하여 전역 변수에 저장하는 작업입니다."""
    print(f"전체 식당 업데이트 시작: {datetime.now()}")
    all_menus = KnuScraper.fetch_all_menus()
    if all_menus:
        handlers.current_menus = all_menus
        print(f"{len(all_menus)}개 식당 데이터 업데이트 완료")
    else:
        print("데이터 업데이트 실패")

if __name__ == '__main__':
    # 프로그램 시작 시 1회 데이터 업데이트 수행
    update_menu_task()
    
    # 매주 월요일 오전 6시에 자동으로 식단을 업데이트하도록 스케줄러 설정
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_menu_task, 'cron', day_of_week='mon', hour=6, minute=0)
    scheduler.start()
    
    # 텔레그램 봇 어플리케이션 빌드
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # 기존 예약 데이터 복구 및 작업 큐 등록
    restore_reservations(app)
    
    # 명령어 및 텍스트 핸들러 등록
    app.add_handler(CommandHandler('start', handlers.start_handler))
    app.add_handler(CommandHandler('help', handlers.start_handler))
    app.add_handler(MessageHandler(filters.Regex(r'^/?(start|help|시작|도움말)$'), handlers.start_handler))
    app.add_handler(CallbackQueryHandler(handlers.menu_callback_handler, pattern="^menu_"))
    app.add_handler(get_conv_handler())
    
    # 식당 이름 및 별칭을 포함한 정규표현식 필터 생성
    all_valid_names = list(config.CAFETERIAS.keys())
    for aliases in config.CAFETERIA_ALIASES.values():
        all_valid_names.extend(aliases)
    cafeteria_names_str = '|'.join(all_valid_names)

    # 점심/저녁/내일 키워드와 식당 이름을 조합한 필터 설정
    cafeteria_pattern = f"^/?(내일\s*)?((저녁|점심)\s*)?({cafeteria_names_str})$"
    general_filter = (
        filters.Regex(r'^/?(내일\s*)?((저녁|점심)\s*)?학식$') | 
        filters.Regex(r'^/?(내일\s*)?(저녁|점심)$') | 
        filters.Regex(r'^/?내일$')
    )
    cafeteria_filter = filters.TEXT & (general_filter | filters.Regex(cafeteria_pattern))
    
    app.add_handler(MessageHandler(cafeteria_filter, handlers.menu_handler))
    
    print("봇 가동 시작 (명령어 대기 중)")
    app.run_polling()