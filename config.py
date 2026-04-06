import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
BASE_URL = "https://coop.knu.ac.kr/sub03/sub01_01.html"

# 요청하신 한국어 명칭과 정확한 ID 매핑
CAFETERIAS = {
    "정보센터식당": "35",
    "복지관 교직원식당": "36",
    "카페테리아 첨성": "37",
    "GP감꽃식당": "46",
    "공식당 교직원식당": "85",
    "공식당 학생식당": "86"
}

# 각 식당별 별명 풀
CAFETERIA_ALIASES = {
    "정보센터식당": ["정센", "정보센터"],
    "복지관 교직원식당": ["복지관교직원"],
    "카페테리아 첨성": ["복지관", "첨성", "카페테리아"],
    "GP감꽃식당": ["감꽃", "감꽃식당", "글플"],
    "공식당 교직원식당": ["공교", "공식당교직원", "공대교직원"],
    "공식당 학생식당": ["공식당", "공학", "공식당학생", "공대"]
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}