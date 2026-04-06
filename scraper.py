import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import config

class KnuScraper:
    @staticmethod
    def fetch_weekly_menu():
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        date_str = monday.strftime('%Y-%m-%d')
        
        url = f"{config.BASE_URL}?shop_sqno={config.SHOP_SQNO}&selDate={date_str}"
        
        try:
            response = requests.get(url, headers=config.HEADERS, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 요일별 데이터를 담을 딕셔너리 초기화
            new_menu = {day: {} for day in ['월', '화', '수', '목', '금', '토']}
            
            # HTML 내의 '중식', '석식' 섹션을 각각 찾음
            sections = soup.select('div.week_table')
            
            for section in sections:
                title_tag = section.select_one('p.title')
                if not title_tag: continue
                category = title_tag.get_text(strip=True) # "중식" 또는 "석식"
                
                # 해당 테이블의 모든 td(요일별 식단) 추출
                tds = section.select('tbody tr td')
                days = ['월', '화', '수', '목', '금', '토']
                
                for i, td in enumerate(tds):
                    if i < len(days):
                        menu_p = td.select_one('li.first p')
                        if menu_p:
                            menu_text = menu_p.get_text("\n", strip=True)
                            new_menu[days[i]][category] = menu_text

            # 데이터가 하나라도 있는지 확인
            if not any(new_menu[d] for d in new_menu):
                return None

            return new_menu
        except Exception as e:
            print(f"Scraping Error: {e}")
            return None