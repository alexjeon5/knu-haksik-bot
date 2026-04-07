import re
from datetime import time
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from bot import config
import bot.handlers as handlers

# 대화 상태(State) 정의
SELECT_ACTION, SELECT_DAYS, SELECT_CAFETERIA, SELECT_TIME = range(4)

DAYS_MAP = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금'}

def get_user_res(context: ContextTypes.DEFAULT_TYPE):
    """유저의 예약 기본값을 가져오거나 설정합니다."""
    if 'reservation' not in context.user_data:
        context.user_data['reservation'] = {
            'days': [0, 1, 2, 3, 4], # 기본값: 월~금
            'cafeterias': ['정보센터식당'], # 기본값: 정보센터식당
            'time': '08:00' # 기본값: 오전 8시
        }
    return context.user_data['reservation']

def format_res_info(res):
    days_str = ", ".join([DAYS_MAP[d] for d in sorted(res['days'])]) if res['days'] else "없음"
    cafes_str = ", ".join(res['cafeterias']) if res['cafeterias'] else "없음"
    return f"📅 <b>요일</b>: {days_str}\n🍽 <b>식당</b>: {cafes_str}\n⏰ <b>시간</b>: {res['time']}"

async def res_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/예약 명령어 입력 시 호출되는 함수"""
    chat_id = update.effective_chat.id
    # 현재 유저에게 등록된 예약 스케줄이 있는지 확인
    jobs = context.job_queue.get_jobs_by_name(f"res_{chat_id}")
    
    if jobs:
        res = context.user_data.get('reservation', get_user_res(context))
        text = f"✅ <b>현재 알림이 설정되어 있습니다.</b>\n\n{format_res_info(res)}\n\n무엇을 하시겠습니까?"
        keyboard = [
            [InlineKeyboardButton("수정하기", callback_data="edit"), InlineKeyboardButton("취소하기", callback_data="delete")]
        ]
    else:
        text = "등록된 예약 알림이 없습니다. 새로 설정하시겠습니까?"
        keyboard = [[InlineKeyboardButton("새 예약 만들기", callback_data="create")]]
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
    return SELECT_ACTION

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "delete":
        chat_id = update.effective_chat.id
        jobs = context.job_queue.get_jobs_by_name(f"res_{chat_id}")
        for job in jobs:
            job.schedule_removal()
        await query.edit_message_text("❌ 예약 알림이 성공적으로 취소되었습니다.")
        return ConversationHandler.END
        
    elif data in ["create", "edit"]:
        res = get_user_res(context)
        keyboard = build_days_keyboard(res)
        await query.edit_message_text(
            "📅 <b>알림을 받을 요일을 선택해주세요.</b> (중복 선택 가능)\n\n설정이 끝나면 [다음] 버튼을 눌러주세요.", 
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return SELECT_DAYS

def build_days_keyboard(res):
    keyboard = []
    row = []
    for d_int, d_str in DAYS_MAP.items():
        mark = "✅" if d_int in res['days'] else "⬜"
        row.append(InlineKeyboardButton(f"{d_str} {mark}", callback_data=f"day_{d_int}"))
    keyboard.append(row)
    keyboard.append([InlineKeyboardButton("➡️ 다음 (식당 선택)", callback_data="next_cafe")])
    return InlineKeyboardMarkup(keyboard)

async def handle_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    res = get_user_res(context)
    
    if data.startswith("day_"):
        d_int = int(data.split("_")[1])
        if d_int in res['days']:
            res['days'].remove(d_int)
        else:
            res['days'].append(d_int)
        
        await query.edit_message_reply_markup(reply_markup=build_days_keyboard(res))
        return SELECT_DAYS
        
    elif data == "next_cafe":
        if not res['days']:
            await query.answer("최소 하루 이상의 요일을 선택해야 합니다.", show_alert=True)
            return SELECT_DAYS
            
        keyboard = build_cafe_keyboard(res)
        await query.edit_message_text(
            "🍽 <b>알림을 받을 식당을 선택해주세요.</b> (중복 선택 가능)\n\n설정이 끝나면 [다음] 버튼을 눌러주세요.", 
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return SELECT_CAFETERIA

def build_cafe_keyboard(res):
    keyboard = []
    names = list(config.CAFETERIAS.keys())
    for i in range(0, len(names), 2):
        row = []
        for cafe in names[i:i+2]:
            mark = "✅" if cafe in res['cafeterias'] else "⬜"
            row.append(InlineKeyboardButton(f"{cafe} {mark}", callback_data=f"cafe_{cafe}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ 이전", callback_data="prev_days"), InlineKeyboardButton("➡️ 다음 (시간 설정)", callback_data="next_time")])
    return InlineKeyboardMarkup(keyboard)

async def handle_cafeterias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    res = get_user_res(context)
    
    if data.startswith("cafe_"):
        cafe = data.split("_")[1]
        if cafe in res['cafeterias']:
            res['cafeterias'].remove(cafe)
        else:
            res['cafeterias'].append(cafe)
            
        await query.edit_message_reply_markup(reply_markup=build_cafe_keyboard(res))
        return SELECT_CAFETERIA
        
    elif data == "prev_days":
        keyboard = build_days_keyboard(res)
        await query.edit_message_text("📅 <b>알림을 받을 요일을 선택해주세요.</b> (중복 선택 가능)", reply_markup=keyboard, parse_mode="HTML")
        return SELECT_DAYS
        
    elif data == "next_time":
        if not res['cafeterias']:
            await query.answer("최소 하나 이상의 식당을 선택해야 합니다.", show_alert=True)
            return SELECT_CAFETERIA
            
        await query.edit_message_text(
            f"⏰ <b>알림을 받을 시간을 입력해주세요.</b>\n"
            f"형식: <code>HH:MM</code> (예: <code>08:30</code>)\n\n"
            f"현재 설정된 시간: <b>{res['time']}</b>\n\n"
            f"<i>(시간을 변경하지 않고 그대로 저장하려면 '유지'라고 입력하세요.)</i>",
            parse_mode="HTML"
        )
        return SELECT_TIME

async def handle_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    res = get_user_res(context)
    
    if text != "유지":
        match = re.match(r"^([01]?[0-9]|2[0-3]):([0-5][0-9])$", text)
        if not match:
            await update.message.reply_text("⚠️ 올바른 형식이 아닙니다. HH:MM 형식으로 입력해주세요. (예: 08:30)")
            return SELECT_TIME
        res['time'] = f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
        
    # 기존에 등록된 스케줄이 있다면 삭제
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(f"res_{chat_id}")
    for job in jobs:
        job.schedule_removal()
        
    # 새 작업 스케줄링
    hour, minute = map(int, res['time'].split(':'))
    # 서버 환경(Docker)이나 로컬과 무관하게 KST(한국 시간) 기준으로 알림 발송
    t = time(hour=hour, minute=minute, tzinfo=ZoneInfo('Asia/Seoul'))
    
    context.job_queue.run_daily(
        send_res_notification,
        time=t,
        days=tuple(res['days']),
        chat_id=chat_id,
        name=f"res_{chat_id}",
        data=res['cafeterias']
    )
    
    await update.message.reply_text(
        f"🎉 <b>예약 알림 설정이 완료되었습니다!</b>\n\n{format_res_info(res)}",
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """대화 도중 /cancel 입력 시 취소"""
    await update.message.reply_text("예약 설정이 취소되었습니다. 처음부터 다시 하려면 /예약 명령어를 입력해주세요.")
    return ConversationHandler.END

async def send_res_notification(context: ContextTypes.DEFAULT_TYPE):
    """실제로 예약된 시간에 메시지를 전송하는 함수"""
    job = context.job
    chat_id = job.chat_id
    cafeterias = job.data
    
    print(f"[*] ⏰ 예약 발송 스케줄러 작동됨! (채팅방: {chat_id}, 대상 식당: {cafeterias})")
    
    import datetime as dt
    now = dt.datetime.now(ZoneInfo('Asia/Seoul'))
    day_str = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
    
    messages_to_send = []
    for cafe in cafeterias:
        cafe_data = handlers.current_menus.get(cafe, {}).get(day_str, {})
        
        # 데이터가 없어도 알림이 무조건 가도록 조건문 제거 및 기본값 설정
        meal_content = cafe_data.get('중식', '오늘은 등록된 식단 정보가 없습니다. (휴무 또는 업데이트 전)')
        
        msg = (
            f"🔔 <b>[예약 알림] 오늘({day_str}) {cafe} 식단</b>\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"☀️ <b>[중식]</b>\n{meal_content}\n\n"
            f"━━━━━━━━━━━━━━"
        )
        messages_to_send.append(msg)
            
    for m in messages_to_send:
        from telegram.constants import ParseMode
        try:
            await context.bot.send_message(chat_id=chat_id, text=m, parse_mode=ParseMode.HTML)
            print(f"[*] ✅ {cafe} 발송 완료!")
        except Exception as e:
            print(f"[!] ❌ 메시지 발송 실패: {e}")
            
    for m in messages_to_send:
        from telegram.constants import ParseMode
        await context.bot.send_message(chat_id=chat_id, text=m, parse_mode=ParseMode.HTML)
        
def get_conv_handler():
    """메인 파일에서 등록할 ConversationHandler 반환"""
    return ConversationHandler(
        # CommandHandler('예약', res_start) 대신 MessageHandler와 정규식을 사용합니다.
        entry_points=[MessageHandler(filters.Regex(r'^/?예약$'), res_start)],
        states={
            SELECT_ACTION: [CallbackQueryHandler(handle_action)],
            SELECT_DAYS: [CallbackQueryHandler(handle_days)],
            SELECT_CAFETERIA: [CallbackQueryHandler(handle_cafeterias)],
            SELECT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time)]
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )