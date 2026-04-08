# bot/analytics.py
import json
import os
from telegram import Update
from telegram.ext import ContextTypes

# 데이터를 저장할 JSON 파일 경로
USER_DATA_FILE = 'data/users.json'

# 중복 체크를 빠르게 하기 위한 메모리 상의 집합(Set)
known_users = set()

def load_users():
    """봇 시작 시 기존에 저장된 사용자 ID 목록을 불러옵니다."""
    global known_users
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                known_users = set(data.get("users", []))
            print(f"[*] 누적 사용자 {len(known_users)}명 로드 완료")
        except Exception as e:
            print(f"[!] 사용자 데이터 로드 실패: {e}")
    else:
        # 파일이 없을 경우 디렉토리 생성
        os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)

def save_user(user_id: int):
    """새로운 사용자를 Set에 추가하고 JSON 파일에 즉시 반영합니다."""
    global known_users
    known_users.add(user_id)
    try:
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            # 최소한의 정보인 user_id 목록과 총 사용자 수만 저장
            json.dump({
                "total_users": len(known_users),
                "users": list(known_users)
            }, f, indent=4)
    except Exception as e:
        print(f"[!] 사용자 데이터 저장 실패: {e}")

async def track_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    모든 종류의 업데이트(메시지, 콜백 등)에서 작동하여 
    새로운 사용자일 경우에만 파일에 기록하는 핸들러입니다.
    """
    if update.effective_user:
        user_id = update.effective_user.id
        if user_id not in known_users:
            save_user(user_id)
            print(f"[*] 새로운 사용자 유입! (현재 총 {len(known_users)}명)")