import requests
import os
import time
import os
from dotenv import load_dotenv, find_dotenv
import json


load_dotenv(find_dotenv())

# --- KONFIGURASI ---
API_KEY = os.getenv("API_BPS")
DOMAIN = "7600" # 7600 = BPS Sulawesi Barat
BASE_URL = "https://webapi.bps.go.id/v1/api"

def download_file(url, folder, filename):
    if not url: return
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    path = os.path.join(folder, filename.replace("/", "-") + ".pdf")
    if os.path.exists(path):
        print(f"Skipping: {filename} (Sudah ada)")
        return

    try:
        while True:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(path, 'wb') as f:
                    f.write(response.content)
                print(f"Berhasil download:  {filename}")
                break
            else:
                print(f"Gagal download {filename}: HTTP {response.status_code}")
                time.sleep(3)
    except Exception as e:
        print(f"Error pada {filename}: {e}")

def fetch_bps_data(model_type, data_json, data_json_old):
    """model_type: 'publication' atau 'pressrelease'"""
    page = 1
    total_pages = 1
    folder_data = os.getenv("PDF_ALL_FOLDER_Publikasi")
    if model_type == 'publication' : 
        folder_data = os.getenv("PDF_ALL_FOLDER_Publikasi")
    elif model_type == 'pressrelease' : 
        folder_data = os.getenv("PDF_ALL_FOLDER_BRS")

    print(f"\n--- Memulai Ingest {model_type.upper()} ---")

    while page <= total_pages:
        url = f"{BASE_URL}/list/model/{model_type}/domain/{DOMAIN}/page/{page}/key/{API_KEY}/"
        response = requests.get(url).json()

        if response['status'] == 'OK':
            # Update total halaman pada iterasi pertama
            if page == 1:
                total_pages = response['data'][0]['pages']
                print(f"Total Halaman: {total_pages}")

            data_list = response['data'][1] 
            
            for item in data_list:
                if model_type == 'publication' : 
                    ada = False
                    title = item['rl_date']+'-'+item['title']

                    for item_old in data_json_old[model_type]:
                        if item_old['pub_id'] == item['pub_id'] :
                            if item_old['rl_date'] != item['rl_date'] or item_old['updt_date'] == item['updt_date'] :
                                if os.path.exists(os.path.join(folder_data, title.replace("/", "-") + ".pdf")):
                                    os.remove(os.path.join(folder_data, title.replace("/", "-") + ".pdf"))
                            else :
                                ada = True
                    if not ada:
                        pdf_url = item['pdf'] 
                        if pdf_url:
                            download_file(pdf_url, folder_data, title)
                elif model_type == 'pressrelease' : 
                    ada = False
                    title = item['rl_date']+'-'+str(item['brs_id'])

                    for item_old in data_json_old[model_type]:
                        if item_old['brs_id'] == item['brs_id'] :
                            if item_old['rl_date'] != item['rl_date'] or item_old['updt_date'] == item['updt_date'] :
                                if os.path.exists(os.path.join(folder_data, title.replace("/", "-") + ".pdf")):
                                    os.remove(os.path.join(folder_data, title.replace("/", "-") + ".pdf"))
                            else :
                                ada = True
                    # Publikasi pakai field 'pdf', BRS biasanya juga 'pdf' atau link langsung
                    pdf_url = item['pdf'] 
                    
                    if pdf_url:
                        download_file(pdf_url, folder_data, title)
                data_json[model_type].append(item)
                break
            page += 1
            time.sleep(1) # Jeda agar tidak terkena rate limit
        else:
            print(f"API Error: {response.get('message')}")
            break
        break

def download_main() :
    data_json = {'publication': [], 'pressrelease': []}
    data_json_old = {'publication': [], 'pressrelease': []}
    if os.path.exists(os.getenv("PDF_JSON")):
        with open(os.getenv("PDF_JSON"), 'r', encoding='utf-8') as file:
            data_json_old = json.load(file)
    fetch_bps_data("publication", data_json, data_json_old)
    fetch_bps_data("pressrelease", data_json, data_json_old)

    with open(os.getenv("PDF_JSON"), 'w') as f:
        json.dump(data_json, f)