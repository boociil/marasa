import requests
import os
import time
import os
from dotenv import load_dotenv, find_dotenv
import json
import threading
from tqdm import tqdm


load_dotenv(find_dotenv())

# --- KONFIGURASI ---
API_KEY = os.getenv("API_BPS")
DOMAIN = "7600" # 7600 = BPS Sulawesi Barat
BASE_URL = "https://webapi.bps.go.id/v1/api"

import string
import unicodedata

INVALID_FILE_CHARS = '/\\?%*:|"<>' # https://en.wikipedia.org/wiki/Filename#Reserved_characters_and_words

def secure_filename(filename):
    # keep only valid ascii chars
    output = list(unicodedata.normalize("NFKD", filename))

    # special case characters that don't get stripped by the above technique
    for pos, char in enumerate(output):
        if char == '\u0141':
            output[pos] = 'L'
        elif char == '\u0142':
            output[pos] = 'l'

    # remove unallowed characters
    output = [c if c not in INVALID_FILE_CHARS else '_' for c in output]
    return "".join(output).encode("ASCII", "ignore").decode()

def range_split(low, up, step):
    arr = range(low,up,step)
    file = []
    for i in range(len(arr)):
        file.append([arr[i],arr[i]+step])
    if file[-1][1]>up:
        file[-1] = [file[-1][0],up]
    return file

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
                # print(f"Berhasil download:  {filename}")
                break
            else:
                # print(f"Gagal download {filename}: HTTP {response.status_code}")
                time.sleep(3)
    except Exception as e:
        print(f"Error pada {filename}: {e}")

def download_file_batch(model_type, data_json):
    folder_data = os.getenv("PDF_ALL_FOLDER_Publikasi")
    if model_type == 'publication' : 
        folder_data = os.getenv("PDF_ALL_FOLDER_Publikasi")
    elif model_type == 'pressrelease' : 
        folder_data = os.getenv("PDF_ALL_FOLDER_BRS")
    need_download = []
    
    for item in data_json[model_type]:
        if model_type == 'publication' : 
            title = secure_filename(item['rl_date']+'-'+item['title'])
            pdf_url = item['pdf'] 
            if pdf_url:
                need_download.append({'url' : pdf_url, 'folder' : folder_data, 'filename': title})
        elif model_type == 'pressrelease' : 
            title = secure_filename(item['rl_date']+'-'+str(item['brs_id'])+'-'+str(item['subj']))
            pdf_url = item['pdf'] 
            if pdf_url:
                need_download.append({'url' : pdf_url, 'folder' : folder_data, 'filename': title})

    print('Download dengan panjang : '+str(len(need_download)))
    
    list_spit_range = range_split(0, len(need_download), 50)
    iiindex = 0
    for item_split_range in list_spit_range :
        print('Iterasi '+model_type+' '+str(iiindex+1)+' dari '+str(len(list_spit_range)))
        threads = list()
        for idx in range(item_split_range[0], item_split_range[1]):
            # print("Main    : create and start thread %d.", site_idx)
            x = threading.Thread(target=download_file, args=(need_download[idx]['url'], need_download[idx]['folder'], need_download[idx]['filename']))
            threads.append(x)
            x.start()

        for index, thread in enumerate(tqdm(threads)):
            # print("Main    : before joining thread {index}.")
            thread.join()
        time.sleep(4)
        iiindex +=1

def fetch_bps_data_list_new(model_type, data_json):
    """model_type: 'publication' atau 'pressrelease'"""
    page = 1
    total_pages = 1

    print(f"\n--- Memulai Ingest {model_type.upper()} ---")

    while page <= total_pages:
        url = f"{BASE_URL}/list/model/{model_type}/domain/{DOMAIN}/page/{page}/key/{API_KEY}/"
        response = requests.get(url).json()
        if response['status'] == 'OK':
            if page == 1:
                total_pages = response['data'][0]['pages']
                print(f"Total Halaman: {total_pages}")
            for item in response['data'][1] :
                data_json[model_type].append(item)
            page += 1
            time.sleep(1) # Jeda agar tidak terkena rate limit

    
def download_pdf_main() :
    data_json = {'publication': [], 'pressrelease': []}
    fetch_bps_data_list_new("pressrelease", data_json)
    print('ada aku disini')
    download_file_batch("pressrelease", data_json)