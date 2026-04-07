# bot/reservation.py
import re
import json
import os
import datetime as dt
from datetime import time
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from bot import config
import bot.handlers as handlers

# 예약 데이터 영구 저장을 위한 JSON 파일 경로
RES_FILE = 'reservations.json'

# 대화형 상태 정의
SELECT_ACTION, SELECT_DAYS, SELECT_CAFETERIA, SELECT_TIME, CONFIRM_DELETE = range(5)
# 요일 숫자와 문자 매핑
DAYS_MAP = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금'}

def load_reservations_from_file():
    """저장된 예약 정보를 JSON 파일에서 불러옵니다."""
    if os.path.exists(RES_FILE):
        if os.path.getsize(RES_FILE) == 0:
            return {}
        try:
            with open(RES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON 로드 실패: {e}")
    return {}

def save_reservation_to_file(chat_id, res_data):
    """사용자의 예약 설정을 JSON 파일에 저장합니다."""
    data = load_reservations_from_file()
    data[str(chat_id)] = res_data
    with open(RES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def delete_reservation_from_file(chat_id):
    """특정 사용자의 예약 데이터를 삭제합니다."""
    data = load_reservations_from_file()
    if str(chat_id) in data:
        del data[str(chat_id)]
        with open(RES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def restore_reservations(app):
    """봇 시작 시 파일에 저장된 모든 예약을 스케줄러에 재등록합니다."""
    data = load_reservations_from_file()
    count = 0
    for chat_id_str, res in data.items():
        chat_id = int(chat_id_str)
        hour, minute = map(int, res['time'].split(':'))
        t = time(hour=hour, minute=minute, tzinfo=ZoneInfo('Asia/Seoul'))
        
        app.job_queue.run_daily(
            send_res_notification,
            t,
            days=tuple(res['days']),
            chat_id=chat_id,
            name=f"res_{chat_id}",
            data=res['cafeterias']
        )
        count += 1
    if count > 0:
        print(f"JSON 파일에서 {count}개의 예약을 복구했습니다.")

def get_user_res(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """사용자의 현재 예약 설정을 가져오거나 기본값을 생성합니다."""
    if 'reservation' not in context.user_data:
        saved_data = load_reservations_from_file()
        if str(chat_id) in saved_data:
            context.user_data['reservation'] = saved_data[str(chat_id)].copy()
        else:
            context.user_data['reservation'] = {
                'days': [0, 1, 2, 3, 4], 
                'cafeterias': ['정보센터식당'], 
                'time': '08:00' 
            }
    return context.user_data['reservation']

def format_res_info(res):
    """사용자가 설정한 예약 내용을 이모지와 함께 텍스트로 변환합니다."""
    days_str = ", ".join([DAYS_MAP[d] for d in sorted(res['days'])]) if res['days'] else "없음"
    cafes_str = ", ".join(res['cafeterias']) if res['cafeterias'] else "없음"
    return f"📅 <b>요일</b>: {days_str}\n🍽 <b>식당</b>: {cafes_str}\n⏰ <b>시간</b>: {res['time']}"

async def res_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """예약 설정 대화를 시작하는 핸들러입니다."""
    chat_id = update.effective_chat.id
    text_input = update.message.text.strip().lstrip('/')
    parts = text_input.split()
    command = parts[1] if len(parts) > 1 else None
    
    jobs = context.job_queue.get_jobs_by_name(f"res_{chat_id}")
    
    if command in ["신규", "수정"]:
        res = get_user_res(context, chat_id)
        keyboard = build_days_keyboard(res)
        await update.message.reply_text("알림을 받을 요일을 선택해주세요 (중복 가능).", reply_markup=keyboard)
        return SELECT_DAYS
        
    elif command == "취소":
        if not jobs:
            await update.message.reply_text("등록된 예약 알림이 없습니다.")
            return ConversationHandler.END
        keyboard = [[InlineKeyboardButton("네, 취소합니다", callback_data="confirm_delete")], [InlineKeyboardButton("아니오, 유지합니다", callback_data="cancel_delete")]]
        await update.message.reply_text("정말로 예약 알림을 취소하시겠습니까?", reply_markup=InlineKeyboardMarkup(keyboard))
        return CONFIRM_DELETE
        
    if jobs:
        res = context.user_data.get('reservation', get_user_res(context, chat_id))
        text = f"현재 알림이 설정되어 있습니다.\n\n{format_res_info(res)}\n\n수행할 작업을 선택하세요."
        keyboard = [[InlineKeyboardButton("수정하기", callback_data="edit"), InlineKeyboardButton("취소하기", callback_data="delete")]]
    else:
        text = "등록된 예약 알림이 없습니다. 새로 설정하시겠습니까?"
        keyboard = [[InlineKeyboardButton("새 예약 만들기", callback_data="create")]]
        
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return SELECT_ACTION

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """메인 예약 메뉴에서 버튼 선택을 처리합니다."""
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    
    if data == "delete":
        keyboard = [[InlineKeyboardButton("네, 취소합니다", callback_data="confirm_delete")], [InlineKeyboardButton("아니오, 유지합니다", callback_data="cancel_delete")]]
        await query.edit_message_text("정말로 예약 알림을 취소하시겠습니까?", reply_markup=InlineKeyboardMarkup(keyboard))
        return CONFIRM_DELETE
    elif data in ["create", "edit"]:
        res = get_user_res(context, chat_id)
        await query.edit_message_text("알림을 받을 요일을 선택해주세요.", reply_markup=build_days_keyboard(res))
        return SELECT_DAYS

async def handle_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """예약 취소 확인 요청을 처리합니다."""
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    
    if data == "confirm_delete":
        for job in context.job_queue.get_jobs_by_name(f"res_{chat_id}"):
            job.schedule_removal()
        if 'reservation' in context.user_data:
            del context.user_data['reservation']
        delete_reservation_from_file(chat_id)
        await query.edit_message_text("예약 알림이 취소되었습니다.")
    else:
        await query.edit_message_text("예약 취소를 철회하고 설정을 유지합니다.")
    return ConversationHandler.END

def build_days_keyboard(res):
    """요일 선택 버튼 키보드를 구성합니다."""
    keyboard = []
    row = []
    for d_int, d_str in DAYS_MAP.items():
        mark = "체크됨" if d_int in res['days'] else "미선택"
        row.append(InlineKeyboardButton(f"{d_str} ({mark})", callback_data=f"day_{d_int}"))
    keyboard.append(row)
    keyboard.append([InlineKeyboardButton("다음 (식당 선택)", callback_data="next_cafe")])
    return InlineKeyboardMarkup(keyboard)

async def handle_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """요일 버튼 클릭을 처리합니다."""
    query = update.callback_query
    await query.answer()
    data = query.data
    res = get_user_res(context, update.effective_chat.id)
    
    if data.startswith("day_"):
        d_int = int(data.split("_")[1])
        if d_int in res['days']: res['days'].remove(d_int)
        else: res['days'].append(d_int)
        await query.edit_message_reply_markup(reply_markup=build_days_keyboard(res))
        return SELECT_DAYS
    elif data == "next_cafe":
        if not res['days']:
            await query.answer("최소 하루 이상 선택해야 합니다.", show_alert=True)
            return SELECT_DAYS
        await query.edit_message_text("알림을 받을 식당을 선택해주세요.", reply_markup=build_cafe_keyboard(res))
        return SELECT_CAFETERIA

def build_cafe_keyboard(res):
    """식당 선택 버튼 키보드를 구성합니다."""
    keyboard = []
    names = list(config.CAFETERIAS.keys())
    for i in range(0, len(names), 2):
        row = []
        for cafe in names[i:i+2]:
            mark = "체크됨" if cafe in res['cafeterias'] else "미선택"
            row.append(InlineKeyboardButton(f"{cafe} ({mark})", callback_data=f"cafe_{cafe}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("이전", callback_data="prev_days"), InlineKeyboardButton("다음 (시간 설정)", callback_data="next_time")])
    return InlineKeyboardMarkup(keyboard)

async def handle_cafeterias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """식당 버튼 클릭을 처리합니다."""
    query = update.callback_query
    await query.answer()
    data = query.data
    res = get_user_res(context, update.effective_chat.id)
    
    if data.startswith("cafe_"):
        cafe = data.split("_")[1]
        if cafe in res['cafeterias']: res['cafeterias'].remove(cafe)
        else: res['cafeterias'].append(cafe)
        await query.edit_message_reply_markup(reply_markup=build_cafe_keyboard(res))
        return SELECT_CAFETERIA
    elif data == "prev_days":
        await query.edit_message_text("알림을 받을 요일을 선택해주세요.", reply_markup=build_days_keyboard(res))
        return SELECT_DAYS
    elif data == "next_time":
        if not res['cafeterias']:
            await query.answer("최소 하나 이상의 식당을 선택해야 합니다.", show_alert=True)
            return SELECT_CAFETERIA
        await query.edit_message_text(f"알림을 받을 시간을 입력해주세요 (형식 HH:MM, 예 08:30).\n현재 시간: {res['time']}")
        return SELECT_TIME

async def handle_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사용자가 입력한 시간을 검증하고 예약을 최종 등록합니다."""
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    res = get_user_res(context, chat_id)
    
    if text != "유지":
        match = re.match(r"^([01]?[0-9]|2[0-3]):([0-5][0-9])$", text)
        if not match:
            await update.message.reply_text("올바른 형식이 아닙니다 (예 08:30).")
            return SELECT_TIME
        res['time'] = f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
        
    for job in context.job_queue.get_jobs_by_name(f"res_{chat_id}"):
        job.schedule_removal()
        
    hour, minute = map(int, res['time'].split(':'))
    t = time(hour=hour, minute=minute, tzinfo=ZoneInfo('Asia/Seoul'))
    
    context.job_queue.run_daily(send_res_notification, t, days=tuple(res['days']), chat_id=chat_id, name=f"res_{chat_id}", data=res['cafeterias'])
    save_reservation_to_file(chat_id, res)
    await update.message.reply_text(f"예약 알림 설정이 완료되었습니다.\n\n{format_res_info(res)}", parse_mode="HTML")
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """예약 설정 대화를 중단합니다."""
    await update.message.reply_text("예약 설정이 취소되었습니다.")
    return ConversationHandler.END

async def send_res_notification(context: ContextTypes.DEFAULT_TYPE):
    """설정된 시간에 맞춰 실제 알림 메시지를 전송하는 함수입니다."""
    job = context.job
    from bot import utils
    date_info = utils.get_target_date_info(is_tomorrow=False)
    
    for cafe in job.data:
        cafe_data = handlers.current_menus.get(cafe, {}).get(date_info["target_day"], {})
        meal_content = cafe_data.get('중식', '등록된 식단 정보가 없습니다.')
        # utils.format_meal_message 호출 시 내부에 이모지가 포함되어 전송됩니다.
        msg = utils.format_meal_message("🔔 예약 알림", date_info["target_day"], cafe, '중식', meal_content)
        try:
            await context.bot.send_message(chat_id=job.chat_id, text=msg, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"메시지 발송 실패: {e}")

def get_conv_handler():
    """메인에서 호출할 예약 기능 전용 대화 핸들러를 반환합니다."""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^/?예약(\s+(신규|수정|취소))?$'), res_start)],
        states={
            SELECT_ACTION: [CallbackQueryHandler(handle_action)],
            SELECT_DAYS: [CallbackQueryHandler(handle_days)],
            SELECT_CAFETERIA: [CallbackQueryHandler(handle_cafeterias)],
            SELECT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time)],
            CONFIRM_DELETE: [CallbackQueryHandler(handle_delete_confirm)] 
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )