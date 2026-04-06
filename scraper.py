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
            sections = soup.select('div.week_table')
            
            for section in sections:
                title_tag = section.select_one('p.title')
                if not title_tag: continue
                category = title_tag.get_text(strip=True)
                
                tds = section.select('tbody tr td')
                days = ['월', '화', '수', '목', '금', '토']
                
                for i, td in enumerate(tds):
                    if i < len(days):
                        # [핵심 수정] li.first p 하나만 찾는 대신, 모든 li 태그를 순회합니다.
                        menu_list = td.select('ul.menu_im li')
                        if menu_list:
                            all_items = []
                            for li in menu_list:
                                # 각 메뉴 항목의 텍스트(메뉴명, 가격 등)를 추출
                                item_text = li.get_text("\n", strip=True)
                                if item_text:
                                    all_items.append(item_text)
                            
                            # 여러 메뉴가 있을 경우 구분선(---)으로 나누어 저장
                            new_menu[days[i]][category] = "\n--------------\n".join(all_items)
            return new_menu
        except Exception as e:
            print(f"[!] {sqno} 수집 에러: {e}")
            return None