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

# JSON 백업 파일 경로 설정
RES_FILE = 'reservations.json'

# 대화 상태(State) 정의 (🌟 CONFIRM_DELETE 상태가 추가되었습니다)
SELECT_ACTION, SELECT_DAYS, SELECT_CAFETERIA, SELECT_TIME, CONFIRM_DELETE = range(5)
DAYS_MAP = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금'}

# --- JSON 백업 관리 함수 ---
def load_reservations_from_file():
    if os.path.exists(RES_FILE):
        if os.path.getsize(RES_FILE) == 0:
            return {}
        try:
            with open(RES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] JSON 예약 데이터 로드 실패: {e}")
    return {}

def save_reservation_to_file(chat_id, res_data):
    data = load_reservations_from_file()
    data[str(chat_id)] = res_data
    with open(RES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def delete_reservation_from_file(chat_id):
    data = load_reservations_from_file()
    if str(chat_id) in data:
        del data[str(chat_id)]
        with open(RES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def restore_reservations(app):
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
        print(f"[*] 💾 JSON 백업 파일에서 {count}개의 예약 데이터를 성공적으로 복구했습니다.")
# ---------------------------

def get_user_res(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
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
    days_str = ", ".join([DAYS_MAP[d] for d in sorted(res['days'])]) if res['days'] else "없음"
    cafes_str = ", ".join(res['cafeterias']) if res['cafeterias'] else "없음"
    return f"📅 <b>요일</b>: {days_str}\n🍽 <b>식당</b>: {cafes_str}\n⏰ <b>시간</b>: {res['time']}"

async def res_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/예약, /예약 신규, /예약 수정, /예약 취소 명령어 입력 시 호출되는 함수"""
    chat_id = update.effective_chat.id
    
    # 입력된 텍스트에서 추가 명령어(신규, 수정, 취소) 분리
    text_input = update.message.text.strip().lstrip('/')
    parts = text_input.split()
    command = parts[1] if len(parts) > 1 else None
    
    jobs = context.job_queue.get_jobs_by_name(f"res_{chat_id}")
    
    # 🌟 1. '예약 신규' 또는 '예약 수정' 입력 시 바로 설정 진입
    if command in ["신규", "수정"]:
        res = get_user_res(context, chat_id)
        keyboard = build_days_keyboard(res)
        await update.message.reply_text(
            "📅 <b>알림을 받을 요일을 선택해주세요.</b> (중복 선택 가능)\n\n설정이 끝나면 [다음] 버튼을 눌러주세요.", 
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return SELECT_DAYS
        
    # 🌟 2. '예약 취소' 입력 시 바로 취소 확인 단계 진입
    elif command == "취소":
        if not jobs:
            await update.message.reply_text("등록된 예약 알림이 없습니다.")
            return ConversationHandler.END
            
        keyboard = [
            [InlineKeyboardButton("네, 취소합니다", callback_data="confirm_delete")],
            [InlineKeyboardButton("아니오, 유지합니다", callback_data="cancel_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("❓ <b>정말로 예약 알림을 취소하시겠습니까?</b>\n모든 설정값이 초기화됩니다.", reply_markup=reply_markup, parse_mode="HTML")
        return CONFIRM_DELETE
        
    # 3. 추가 인자 없이 '예약'만 입력했을 때 (기존 메뉴 표시)
    if jobs:
        res = context.user_data.get('reservation', get_user_res(context, chat_id))
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
    chat_id = update.effective_chat.id
    
    # 🌟 기존 메뉴에서 '취소하기' 버튼을 눌렀을 때도 확인(Confirm) 메시지를 띄웁니다.
    if data == "delete":
        keyboard = [
            [InlineKeyboardButton("네, 취소합니다", callback_data="confirm_delete")],
            [InlineKeyboardButton("아니오, 유지합니다", callback_data="cancel_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❓ <b>정말로 예약 알림을 취소하시겠습니까?</b>\n모든 설정값이 초기화됩니다.", reply_markup=reply_markup, parse_mode="HTML")
        return CONFIRM_DELETE
        
    elif data in ["create", "edit"]:
        res = get_user_res(context, chat_id)
        keyboard = build_days_keyboard(res)
        await query.edit_message_text(
            "📅 <b>알림을 받을 요일을 선택해주세요.</b> (중복 선택 가능)\n\n설정이 끝나면 [다음] 버튼을 눌러주세요.", 
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return SELECT_DAYS

# 🌟 [신규] 취소 확인(Confirm) 버튼 처리 핸들러
async def handle_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    
    if data == "confirm_delete":
        # 사용자가 진짜로 '네'를 눌렀을 때만 데이터 삭제 로직 실행
        jobs = context.job_queue.get_jobs_by_name(f"res_{chat_id}")
        for job in jobs:
            job.schedule_removal()
        
        if 'reservation' in context.user_data:
            del context.user_data['reservation']
        delete_reservation_from_file(chat_id)
        print(f"[*] 🗑 {chat_id} 유저의 예약 설정값이 초기화 및 삭제되었습니다.")
            
        await query.edit_message_text("❌ 예약 알림이 취소되었으며, 모든 설정값이 초기화되었습니다.")
    else:
        # '아니오'를 누른 경우
        await query.edit_message_text("✅ 예약 알림 취소를 철회하고 기존 설정을 유지합니다.")
        
    return ConversationHandler.END

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
    chat_id = update.effective_chat.id
    res = get_user_res(context, chat_id)
    
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
    chat_id = update.effective_chat.id
    res = get_user_res(context, chat_id)
    
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
            f"24시간 형식으로 입력해주세요. (예: <code>08:30</code>)\n\n"
            f"현재 설정된 시간: <b>{res['time']}</b>\n\n"
            f"<i>(시간을 변경하지 않고 그대로 저장하려면 '유지'라고 입력하세요.)</i>",
            parse_mode="HTML"
        )
        return SELECT_TIME

async def handle_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    res = get_user_res(context, chat_id)
    
    if text != "유지":
        match = re.match(r"^([01]?[0-9]|2[0-3]):([0-5][0-9])$", text)
        if not match:
            await update.message.reply_text("⚠️ 올바른 형식이 아닙니다. HH:MM 형식으로 입력해주세요. (예: 08:30)")
            return SELECT_TIME
        res['time'] = f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
        
    jobs = context.job_queue.get_jobs_by_name(f"res_{chat_id}")
    for job in jobs:
        job.schedule_removal()
        
    hour, minute = map(int, res['time'].split(':'))
    t = time(hour=hour, minute=minute, tzinfo=ZoneInfo('Asia/Seoul'))
    
    context.job_queue.run_daily(
        send_res_notification,
        t,
        days=tuple(res['days']),
        chat_id=chat_id,
        name=f"res_{chat_id}",
        data=res['cafeterias']
    )
    
    save_reservation_to_file(chat_id, res)
    
    await update.message.reply_text(
        f"🎉 <b>예약 알림 설정이 완료되었습니다!</b>\n\n{format_res_info(res)}",
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("예약 설정이 취소되었습니다. 처음부터 다시 하려면 /예약 명령어를 입력해주세요.")
    return ConversationHandler.END

async def send_res_notification(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    cafeterias = job.data
    
    # 🌟 [변경] 유틸리티를 사용하여 오늘 요일 정보를 가져옵니다.
    from bot import utils
    date_info = utils.get_target_date_info(is_tomorrow=False)
    
    for cafe in cafeterias:
        cafe_data = handlers.current_menus.get(cafe, {}).get(date_info["target_day"], {})
        # 예약 알림은 기본적으로 중식 메뉴를 보낸다고 가정 (필요시 수정 가능)
        meal_content = cafe_data.get('중식', '오늘은 등록된 식단 정보가 없습니다. (휴무 또는 업데이트 전)')
        
        # 🌟 [변경] 공통 메시지 포맷팅 함수 사용
        msg = utils.format_meal_message(
            "🔔 예약 알림", date_info["target_day"], cafe, '중식', meal_content
        )
        
        from telegram.constants import ParseMode
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.HTML)
            print(f"[*] ✅ {cafe} 발송 완료!")
        except Exception as e:
            print(f"[!] ❌ {cafe} 메시지 발송 실패: {e}")
        
def get_conv_handler():
    """메인 파일에서 등록할 ConversationHandler 반환"""
    print("[*] 예약 기능 핸들러가 정상적으로 등록(활성화) 되었습니다.")
    return ConversationHandler(
        # 🌟 정규식을 업데이트하여 '신규', '수정', '취소' 인자를 모두 감지할 수 있도록 하였습니다.
        entry_points=[MessageHandler(filters.Regex(r'^/?예약(\s+(신규|수정|취소))?$'), res_start)],
        states={
            SELECT_ACTION: [CallbackQueryHandler(handle_action)],
            SELECT_DAYS: [CallbackQueryHandler(handle_days)],
            SELECT_CAFETERIA: [CallbackQueryHandler(handle_cafeterias)],
            SELECT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time)],
            # 🌟 [신규] '정말 삭제하시겠습니까?'를 처리하는 상태가 추가되었습니다.
            CONFIRM_DELETE: [CallbackQueryHandler(handle_delete_confirm)] 
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )