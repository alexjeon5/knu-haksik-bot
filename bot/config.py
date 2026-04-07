# bot/config.py
import os
from dotenv import load_dotenv

# .env 파일로부터 환경 변수를 로드합니다.
load_dotenv()

# 텔레그램 봇 API 토큰
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
# 경북대학교 생협 식단 페이지 URL
BASE_URL = "https://coop.knu.ac.kr/sub03/sub01_01.html"

# 시스템 내부에서 사용하는 공식 식당 명칭과 고유 ID 매핑
CAFETERIAS = {
    "정보센터식당": "35",
    "복지관 교직원식당": "36",
    "카페테리아 첨성": "37",
    "GP감꽃식당": "46",
    "공식당 교직원식당": "85",
    "공식당 학생식당": "86"
}

# 사용자가 입력할 수 있는 식당별 별칭 목록
CAFETERIA_ALIASES = {
    "정보센터식당": ["정센", "정보센터"],
    "복지관 교직원식당": ["복지관교직원"],
    "카페테리아 첨성": ["복지관", "첨성", "카페테리아"],
    "GP감꽃식당": ["감꽃", "감꽃식당", "글플"],
    "공식당 교직원식당": ["공교", "공식당교직원", "공대교직원"],
    "공식당 학생식당": ["공식당", "공학", "공식당학생", "공대"]
}

# 웹 크롤링 시 사용하는 브라우저 헤더 설정
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

def find_cafeteria(text):
    """
    사용자가 입력한 텍스트를 분석하여 공식 식당 명칭을 찾아 반환하는 함수입니다.
    공식 명칭 매칭 후 별칭 목록을 순회하며 매칭 여부를 확인합니다.
    """
    # 1. 공식 명칭 매칭 확인
    for cafe in CAFETERIAS.keys():
        if cafe in text:
            return cafe
    # 2. 별칭 목록 매칭 확인
    for official_name, aliases in CAFETERIA_ALIASES.items():
        for alias in aliases:
            if alias in text:
                return official_name
    return None