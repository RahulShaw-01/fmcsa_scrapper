from flask import Flask, render_template, request, send_file
import cloudscraper
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
from io import BytesIO

app = Flask(__name__)

# US State to Timezone Mapping
TIMEZONE_MAP = {
    'ME': 'EST', 'VT': 'EST', 'NH': 'EST', 'MA': 'EST', 'RI': 'EST', 'CT': 'EST', 'NY': 'EST', 'NJ': 'EST', 'PA': 'EST', 'DE': 'EST', 'MD': 'EST', 'DC': 'EST', 'VA': 'EST', 'WV': 'EST', 'NC': 'EST', 'SC': 'EST', 'GA': 'EST', 'FL': 'EST', 'OH': 'EST', 'MI': 'EST', 'IN': 'EST', 'KY': 'EST',
    'IL': 'CST', 'WI': 'CST', 'MN': 'CST', 'IA': 'CST', 'MO': 'CST', 'ND': 'CST', 'SD': 'CST', 'NE': 'CST', 'KS': 'CST', 'OK': 'CST', 'TX': 'CST', 'TN': 'CST', 'AL': 'CST', 'MS': 'CST', 'AR': 'CST', 'LA': 'CST',
    'MT': 'MST', 'ID': 'MST', 'WY': 'MST', 'CO': 'MST', 'NM': 'MST', 'AZ': 'MST', 'UT': 'MST',
    'CA': 'PST', 'NV': 'PST', 'OR': 'PST', 'WA': 'PST'
}

def get_data(mc):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    url = f"https://safer.fmcsa.dot.gov/query.asp?searchtype=ANY&query_type=queryCarrierSnapshot&query_param=MC_MX&query_string={mc}"
    
    try:
        time.sleep(1.2)
        response = scraper.get(url, timeout=20)
        if response.status_code != 200 or "Company Snapshot" not in response.text:
            return {"MC": mc, "Name": "NOT FOUND", "Phone": "N/A", "Address": "N/A", "Timeline": "N/A"}

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Sirf Legal Name nikalna (No DBA)
        name_label = soup.find(string=re.compile("Legal Name", re.I))
        legal_name = name_label.find_next('td').get_text(strip=True) if name_label else "N/A"

        # Address & Timeline Logic
        phys_td = soup.find('td', id='physicaladdressvalue')
        p_addr = phys_td.get_text(separator=" ", strip=True) if phys_td else "N/A"
        
        timeline = "N/A"
        state_match = re.search(r'\b([A-Z]{2})\b\s+\d{5}', p_addr)
        if state_match:
            state_code = state_match.group(1)
            timeline = TIMEZONE_MAP.get(state_code, "Check State")

        # Phone Extraction
        phone = "N/A"
        for td in soup.find_all('td', class_='queryfield'):
            txt = td.get_text(strip=True)
            if re.search(r'\(\d{3}\)\s\d{3}-\d{4}', txt):
                phone = re.sub(r'\D', '', txt) 
                break

        return {
            "MC": mc, 
            "Name": legal_name, 
            "Phone": phone, 
            "Address": p_addr, 
            "Timeline": timeline
        }
    except Exception:
        return {"MC": mc, "Name": "Error", "Phone": "N/A", "Address": "N/A", "Timeline": "N/A"}

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    mc_raw = ""
    if request.method == 'POST':
        mc_raw = request.form.get('mcs')
        mc_list = re.findall(r'\d+', mc_raw)
        
        # Results Scraping
        results = [get_data(mc) for mc in mc_list]

        # Download Logic
        if 'download' in request.form:
            df = pd.DataFrame(results)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            return send_file(output, download_name="FMCSA_Leads.xlsx", as_attachment=True)
        
    return render_template('index.html', results=results, mc_raw=mc_raw)

if __name__ == '__main__':
    app.run(debug=True)