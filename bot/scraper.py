# bot/scraper.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from bot import config

class KnuScraper:
    @staticmethod
    def fetch_all_menus():
        """
        config에 등록된 모든 식당의 주간 식단을 수집하여 반환합니다.
        """
        all_data = {}
        for name, sqno in config.CAFETERIAS.items():
            print(f"[*] {name} 데이터 수집 중...")
            menu = KnuScraper.fetch_single_menu(sqno)
            if menu:
                all_data[name] = menu
        return all_data

    @staticmethod
    def fetch_single_menu(sqno, date_str=None):
        """
        특정 식당(sqno)의 특정 날짜(date_str) 기준 주간 식단을 크롤링합니다.
        날짜가 지정되지 않으면 이번 주 월요일을 기준으로 조회합니다.
        """
        if not date_str:
            # 기준 날짜가 없으면 현재 날짜로부터 이번 주 월요일 계산
            today = datetime.now()
            monday = today - timedelta(days=today.weekday())
            date_str = monday.strftime('%Y-%m-%d')
            
        url = f"{config.BASE_URL}?shop_sqno={sqno}&selDate={date_str}"
        
        try:
            # 타임아웃 10초 설정하여 페이지 요청
            response = requests.get(url, headers=config.HEADERS, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 월요일부터 토요일까지의 데이터를 담을 딕셔너리 초기화
            new_menu = {day: {} for day in ['월', '화', '수', '목', '금', '토']}
            sections = soup.select('div.week_table')
            
            for section in sections:
                title_tag = section.select_one('p.title')
                if not title_tag: continue
                # 카테고리(중식, 석식 등) 추출
                category = title_tag.get_text(strip=True)
                
                days = ['월', '화', '수', '목', '금', '토']
                daily_blocks = {day: [] for day in days}
                
                # 테이블의 각 행(tr)을 순회하며 요일별 메뉴 추출
                trs = section.select('tbody tr')
                for tr in trs:
                    tds = tr.select('td')
                    
                    for i, td in enumerate(tds):
                        if i >= len(days): continue
                        current_day = days[i]
                        current_label = ""
                        
                        # 메뉴의 세부 라벨(정식, 일품 등)과 품목 리스트 파싱
                        for child in td.find_all(recursive=False):
                            if child.name == 'div' and 'button_m' in child.get('class', []):
                                current_label = child.get_text(strip=True)
                            
                            elif child.name == 'ul' and 'menu_im' in child.get('class', []):
                                items = []
                                for li in child.select('li'):
                                    item_text = li.get_text("\n", strip=True)
                                    # '정식'으로 시작하는 문구 제거 로직 유지
                                    if item_text.startswith("정식"):
                                        item_text = item_text[2:].strip()
                                    if item_text:
                                        items.append(item_text)
                                
                                if items:
                                    # 라벨이 있으면 굵게 표시하고 구분선으로 연결
                                    header = f"<b>[{current_label}]</b>\n" if current_label else ""
                                    item_separator = "\n" + "-" * 25 + "\n"
                                    daily_blocks[current_day].append(header + item_separator.join(items))
                                
                                current_label = ""
                
                # 수집된 데이터를 최종 딕셔너리에 저장
                for day in days:
                    if daily_blocks[day]:
                        group_separator = "\n\n" 
                        new_menu[day][category] = group_separator.join(daily_blocks[day])
            
            return new_menu
        except Exception as e:
            # 수집 중 에러 발생 시 로그 출력
            print(f"[!] {sqno} 수집 에러: {e}")
            return None