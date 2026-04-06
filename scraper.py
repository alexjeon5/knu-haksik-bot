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
            # 웹사이트 접속 및 HTML 파싱
            response = requests.get(url, headers=config.HEADERS, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            new_menu = {day: {} for day in ['월', '화', '수', '목', '금', '토']}
            sections = soup.select('div.week_table')
            
            for section in sections:
                title_tag = section.select_one('p.title')
                if not title_tag: continue
                category = title_tag.get_text(strip=True)
                
                days = ['월', '화', '수', '목', '금', '토']
                
                # 요일별로 메뉴 블록을 차곡차곡 모아둘 딕셔너리 준비
                daily_blocks = {day: [] for day in days}
                
                # [수정 핵심] tbody 안의 '모든' tr을 순회하도록 변경하여 여러 줄(뚝배기, 특식 등)을 모두 파싱
                trs = section.select('tbody tr')
                for tr in trs:
                    tds = tr.select('td')
                    
                    for i, td in enumerate(tds):
                        if i >= len(days): continue
                        current_day = days[i]
                        
                        current_label = ""
                        
                        # td 내부의 모든 요소를 순차적으로 분석
                        for child in td.find_all(recursive=False):
                            if child.name == 'div' and 'button_m' in child.get('class', []):
                                current_label = child.get_text(strip=True)
                            
                            elif child.name == 'ul' and 'menu_im' in child.get('class', []):
                                items = []
                                for li in child.select('li'):
                                    item_text = li.get_text("\n", strip=True)
                                    if item_text.startswith("정식"):
                                        item_text = item_text[2:].strip()
                                    if item_text:
                                        items.append(item_text)
                                
                                if items:
                                    header = f"<b>[{current_label}]</b>\n" if current_label else ""
                                    
                                    # 개별 메뉴(<li>) 사이사이에 점선 삽입
                                    item_separator = "\n" + "-" * 25 + "\n"
                                    daily_blocks[current_day].append(header + item_separator.join(items))
                                
                                current_label = ""
                
                # 수집된 요일별 블록들을 합쳐서 최종 식단 딕셔너리에 저장
                for day in days:
                    if daily_blocks[day]:
                        # 뚝배기, 특식 등 서로 다른 그룹 사이는 줄바꿈 2번(\n\n)으로 깔끔하게 띄워줌
                        group_separator = "\n\n" 
                        new_menu[day][category] = group_separator.join(daily_blocks[day])
                    
            
            return new_menu
        except Exception as e:
            print(f"[!] {sqno} 수집 에러: {e}")
            return None