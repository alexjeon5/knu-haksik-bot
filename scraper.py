import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import config

class KnuScraper:
    @staticmethod
    def fetch_all_menus():
        all_data = {}
        for name, sqno in config.CAFETERIAS.items():
            print(f"[*] {name} 데이터 수집 중...")
            menu = KnuScraper.fetch_single_menu(sqno)
            if menu:
                all_data[name] = menu
        return all_data

    @staticmethod
    def fetch_single_menu(sqno):
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        date_str = monday.strftime('%Y-%m-%d')
        url = f"{config.BASE_URL}?shop_sqno={sqno}&selDate={date_str}"
        
        try:
            response = requests.get(url, headers=config.HEADERS, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            new_menu = {day: {} for day in ['월', '화', '수', '목', '금', '토']}
            # 중식/석식 섹션을 구분하여 긁어오는 핵심 로직
            sections = soup.select('div.week_table')
            
            for section in sections:
                title_tag = section.select_one('p.title')
                if not title_tag: continue
                category = title_tag.get_text(strip=True) # "중식" 또는 "석식"
                
                tds = section.select('tbody tr td')
                days = ['월', '화', '수', '목', '금', '토']
                
                for i, td in enumerate(tds):
                    if i < len(days):
                        # 메뉴 내용이 담긴 p 태그 타겟팅
                        menu_p = td.select_one('li.first p')
                        if menu_p:
                            menu_text = menu_p.get_text("\n", strip=True)
                            new_menu[days[i]][category] = menu_text
            return new_menu
        except Exception as e:
            print(f"[!] {sqno} 수집 에러: {e}")
            return None