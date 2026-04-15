import requests
import os
import time
import os
from dotenv import load_dotenv, find_dotenv


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
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(path, 'wb') as f:
                f.write(response.content)
            print(f"Berhasil: {filename}")
        else:
            print(f"Gagal download {filename}: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error pada {filename}: {e}")

def fetch_bps_data(model_type):
    """model_type: 'publication' atau 'pressrelease'"""
    page = 1
    total_pages = 1
    folder_name = f"downloads_{DOMAIN}_{model_type}"
    
    print(f"\n--- Memulai Ingest {model_type.upper()} ---")

    while page <= total_pages:
        url = f"{BASE_URL}/list/model/{model_type}/domain/{DOMAIN}/page/{page}/key/{API_KEY}/"
        response = requests.get(url).json()

        if response['status'] == 'OK':
            # Update total halaman pada iterasi pertama
            if page == 1:
                total_pages = response['pagination']['total_pages']
                print(f"Total Halaman: {total_pages}")

            data_list = response['data'][1] # Index [1] berisi list data publikasi/brs
            
            for item in data_list:
                title = item.get('title')
                # Publikasi pakai field 'pdf', BRS biasanya juga 'pdf' atau link langsung
                pdf_url = item.get('pdf') 
                
                if pdf_url:
                    download_file(pdf_url, folder_name, title)
                
            page += 1
            time.sleep(1) # Jeda agar tidak terkena rate limit
        else:
            print(f"API Error: {response.get('message')}")
            break

def download_main() :
    fetch_bps_data("publication")
    fetch_bps_data("pressrelease")