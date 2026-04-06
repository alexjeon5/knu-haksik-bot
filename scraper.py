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
                
                days = ['월', '화', '수', '목', '금', '토']
                
                daily_blocks = {day: [] for day in days}
                
                trs = section.select('tbody tr')
                for tr in trs:
                    tds = tr.select('td')
                    
                    for i, td in enumerate(tds):
                        if i >= len(days): continue
                        current_day = days[i]
                        
                        current_label = ""
                        
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
                                    item_separator = "\n" + "-" * 25 + "\n"
                                    daily_blocks[current_day].append(header + item_separator.join(items))
                                
                                current_label = ""
                
                for day in days:
                    if daily_blocks[day]:
                        group_separator = "\n\n" 
                        new_menu[day][category] = group_separator.join(daily_blocks[day])
            
            return new_menu
        except Exception as e:
            print(f"[!] {sqno} 수집 에러: {e}")
            return None