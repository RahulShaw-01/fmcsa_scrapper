from flask import Flask, render_template, request, send_file
import cloudscraper
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
from io import BytesIO

app = Flask(__name__)

def get_data(mc):
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    url = f"https://safer.fmcsa.dot.gov/query.asp?searchtype=ANY&query_type=queryCarrierSnapshot&query_param=MC_MX&query_string={mc}"
    
    try:
        time.sleep(1.5) 
        response = scraper.get(url, timeout=20)
        
        if response.status_code != 200 or "Company Snapshot" not in response.text:
            return {"MC": mc, "Name": "NOT FOUND/BLOCKED", "Phone": "N/A", "Physical_Address": "N/A"}

        soup = BeautifulSoup(response.content, 'html.parser')
        
        phys_td = soup.find('td', id='physicaladdressvalue')
        p_addr = phys_td.get_text(separator=" ", strip=True) if phys_td else "N/A"
        
        name_label = soup.find(string=re.compile("Legal Name", re.I))
        name = name_label.find_next('td').get_text(strip=True) if name_label else "N/A"
        
        phone = "N/A"
        for td in soup.find_all('td', class_='queryfield'):
            txt = td.get_text(strip=True)
            if re.search(r'\(\d{3}\)\s\d{3}-\d{4}', txt):
                phone = re.sub(r'\D', '', txt)
                break

        return {"MC": mc, "Name": name, "Phone": phone, "Physical_Address": p_addr}
    
    except Exception:
        return {"MC": mc, "Name": "Timeout Error", "Phone": "N/A", "Physical_Address": "N/A"}

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    mc_raw = ""
    if request.method == 'POST':
        mc_raw = request.form.get('mcs')
        mc_list = re.findall(r'\d+', mc_raw)
        
        if 'download' in request.form:
            results = [get_data(mc) for mc in mc_list]
            df = pd.DataFrame(results)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            return send_file(output, download_name="Lucas_Leads.xlsx", as_attachment=True)
        
        results = [get_data(mc) for mc in mc_list]
            
    return render_template('index.html', results=results, mc_raw=mc_raw)

if __name__ == '__main__':
    app.run(debug=True)