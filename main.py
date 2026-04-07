from bot import config
from bot import handlers
from bot.reservation import get_conv_handler, restore_reservations
from bot.scraper import KnuScraper
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters
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

    restore_reservations(app)
    
    # 시작/도움말을 / 기호 없이 한글로 쳐도 작동하게 만듦
    app.add_handler(CommandHandler('start', handlers.start_handler))
    app.add_handler(CommandHandler('help', handlers.start_handler))
    app.add_handler(MessageHandler(filters.Regex(r'^/?(start|help|시작|도움말)$'), handlers.start_handler))

    app.add_handler(CallbackQueryHandler(handlers.menu_callback_handler, pattern="^menu_"))
    
    app.add_handler(get_conv_handler())
    
    all_valid_names = list(config.CAFETERIAS.keys())
    for aliases in config.CAFETERIA_ALIASES.values():
        all_valid_names.extend(aliases)
        
    cafeteria_names_str = '|'.join(all_valid_names)

    # 패턴 맨 앞에 '/?' 를 추가하여 슬래시(/) 허용 및 '점심' 키워드 추가
    cafeteria_pattern = f"^/?(내일\s*)?((저녁|점심)\s*)?({cafeteria_names_str})$"

    # '학식' 키워드 없이 '점심'만 입력하거나 '내일 점심'을 입력해도 동작하도록 필터 확장
    general_filter = (
        filters.Regex(r'^/?(내일\s*)?((저녁|점심)\s*)?학식$') | 
        filters.Regex(r'^/?(내일\s*)?(저녁|점심)$') | 
        filters.Regex(r'^/?내일$')
    )

    cafeteria_filter = filters.TEXT & (general_filter | filters.Regex(cafeteria_pattern))
    
    app.add_handler(MessageHandler(cafeteria_filter, handlers.menu_handler))
    
    print("[*] 봇 가동 중... (명령어 대기)")
    app.run_polling()