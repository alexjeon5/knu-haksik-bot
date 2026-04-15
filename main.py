# main.py
import datetime as dt  # datetime을 dt라는 별칭으로 가져옵니다
from zoneinfo import ZoneInfo  # 시간대 설정을 위해 필요합니다
from bot import config, handlers
from bot.reservation import get_conv_handler, restore_reservations
from bot.scraper import KnuScraper
from telegram.ext import (
    ApplicationBuilder, 
    MessageHandler, 
    CommandHandler, 
    CallbackQueryHandler, 
    filters, 
    TypeHandler,
    ContextTypes  # 이 부분을 추가하세요!
)
from telegram import Update
from bot import analytics
import re
import logging

# 기본 로깅 설정 (INFO 레벨 이상의 에러를 출력)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # level=logging.INFO
    level=logging.ERROR
)
logger = logging.getLogger(__name__)

async def update_menu_task(context: ContextTypes.DEFAULT_TYPE = None):
    """전체 식당의 주간 식단 데이터를 크롤링하여 전역 변수에 저장하는 작업입니다."""
    print(f"전체 식당 업데이트 시작: {dt.datetime.now()}") 
    all_menus = KnuScraper.fetch_all_menus()
    if all_menus:
        handlers.current_menus = all_menus
        print(f"{len(all_menus)}개 식당 데이터 업데이트 완료")
    else:
        print("데이터 업데이트 실패")

if __name__ == '__main__': 
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    
    # 3. 봇이 시작될 때 즉시 1회 실행하도록 JobQueue에 등록 (when=0)
    app.job_queue.run_once(update_menu_task, when=0)
    
    # 4. 매주 월요일 6시 실행 설정 (lambda 제거하고 함수 이름만 전달)
    app.job_queue.run_daily(
        update_menu_task, 
        time=dt.time(hour=6, minute=0, tzinfo=ZoneInfo('Asia/Seoul')),
        days=(0,) # 월요일
    )
    restore_reservations(app)

    # ============== 사용자 수집 핸들러 추가 ==============
    # group=-1 로 설정하여 다른 일반 핸들러들보다 먼저 실행되게 하고, 
    # 이벤트 소비를 막아 정상적으로 기존 기능들도 작동하게 합니다.
    app.add_handler(TypeHandler(Update, analytics.track_user_handler), group=-1)
    
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
