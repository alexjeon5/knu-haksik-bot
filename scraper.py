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
                
                tds = section.select('tbody tr td')
                days = ['월', '화', '수', '목', '금', '토']
                
                for i, td in enumerate(tds):
                    if i >= len(days): continue
                    
                    menu_blocks = []
                    current_label = ""
                    
                    # td 내부 요소를 순회하며 제목(뚝배기 등)과 메뉴 리스트를 매칭
                    for child in td.children:
                        # 카테고리 레이블(뚝배기, 특식 등) 발견 시 저장
                        if child.name == 'div' and 'button_m' in child.get('class', []):
                            current_label = child.get_text(strip=True)
                        
                        # 메뉴 리스트 발견 시 처리
                        elif child.name == 'ul' and 'menu_im' in child.get('class', []):
                            items = []
                            for li in child.select('li'):
                                item_text = li.get_text("\n", strip=True)
                                
                                # 이전 요청사항: "정식" 문구 제거
                                if item_text.startswith("정식"):
                                    item_text = item_text[2:].strip()
                                
                                if item_text:
                                    items.append(item_text)
                            
                            if items:
                                # [핵심 수정] 레이블이 "뚝배기"일 때만 헤더 표시
                                header = f"[{current_label}]\n" if current_label == "뚝배기" else ""
                                menu_blocks.append(header + "\n".join(items))
                            
                            # 레이블 정보 초기화
                            current_label = ""
                    
                    if menu_blocks:
                        new_menu[days[i]][category] = "\n--------------\n".join(menu_blocks)
            
            return new_menu
        except Exception as e:
            print(f"[!] {sqno} 수집 에러: {e}")
            return None