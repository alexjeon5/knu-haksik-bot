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
            
            tables = soup.find_all('table')
            target_table = None
            for t in tables:
                t_text = t.get_text()
                if '월' in t_text and ('분류' in t_text or '중식' in t_text):
                    target_table = t
                    break
            
            if not target_table: return None

            rows = target_table.find_all('tr')
            header_cols = rows[0].find_all(['th', 'td'])
            day_indices = {d: i for i, col in enumerate(header_cols) 
                           for d in ['월', '화', '수', '목', '금'] if d in col.get_text()}
            
            new_menu = {}
            for r in rows[1:]:
                cols = r.find_all(['th', 'td'])
                for day, idx in day_indices.items():
                    if idx < len(cols):
                        menu_text = cols[idx].get_text("\n", strip=True)
                        new_menu[day] = new_menu.get(day, "") + ("\n\n" + menu_text if day in new_menu else menu_text)
            
            return new_menu
        except Exception as e:
            print(f"Scraping Error: {e}")
            return None