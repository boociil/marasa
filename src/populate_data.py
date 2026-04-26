import os
import requests
from langchain_core.documents import Document
from src.get_embedding_function import get_embedding_function
from langchain_chroma import Chroma
import os, re, time
from dotenv import load_dotenv, find_dotenv
import html

# 1. LOAD ENV (Parent Folder)
load_dotenv(find_dotenv())
API_KEY = os.getenv("API_BPS")
DOMAIN = "7600"
BASE_URL = "https://webapi.bps.go.id/v1/api"
CHROMA_PATH = os.getenv('CHROMA_PATH_TABLE')

def get_categories():
    """Mengambil semua subjek (CSA) yang tersedia"""
    url = f"{BASE_URL}/list/model/subcatcsa/domain/{DOMAIN}/key/{API_KEY}/"
    while True: 
        try:
            response = requests.get(url).json()
            # print(response)
            if response['status'] == 'OK':
                return response['data'][1]
        except Exception as e:
            print(e)
       



def get_subjects(subcat, page ):
    """Mengambil semua subjek (CSA) yang tersedia"""
    url = f"{BASE_URL}/list/model/subjectcsa/domain/{DOMAIN}/subcat/{subcat}/page/{page}/key/{API_KEY}/"
    # print(url)
    while True: 
        try:
            response = requests.get(url).json()
            # print(response)
            if response['status'] == 'OK':
                return response['data'][1], response['data'][0]['pages']
        except Exception as e:
            print(e)
        
        
def get_table(subject, page):
    """Mengambil semua subjek (CSA) yang tersedia"""
    url = f"{BASE_URL}/list/model/tablestatistic/domain/{DOMAIN}/subject/{subject}/page/{page}/key/{API_KEY}/"
    # print(url)
    while True: 
        try:
            response = requests.get(url).json()
            # print(response)
            if response['data-availability'] == 'list-not-available' :
                return [], None
            if response['status'] == 'OK' and response['data-availability'] != 'list-not-available':
                return response['data'][1], response['data'][0]['pages']
        except Exception as e:
            print(e)
        
        

def get_detail_table(id , type = 0, year_arr = []):
    if len(year_arr) == 0 :
        """Mengambil semua subjek (CSA) yang tersedia"""
        url = f"{BASE_URL}/view/model/tablestatistic/domain/{DOMAIN}/lang/ind/id/{id}/key/{API_KEY}/"
        # print(url)
        while True: 
            try:
                response = requests.get(url).json()
                # print(response)
                if response['status'] == 'OK':
                    return [response]
                elif response['status'] == 'Error':
                    print(response)
                    return []
            except Exception as e:
                print(e)
            
    elif type == 2:
        response_arr = []
        url = f"{BASE_URL}/view/model/tablestatistic/domain/{DOMAIN}/lang/ind/id/{id}/key/{API_KEY}/"
        vars_arr = []
        while True: 
            try:
                response = requests.get(url).json()
                # print(response)
                if response['status'] == 'OK':
                    vars_arr = response['var']
                    break
                elif response['status'] == 'Error':
                    print(response)
                    break
            except Exception as e:
                print(e)

        for item_var in vars_arr :
            page_1 = 1
            pages_1 = 1 
            tahun_arr = []
            while page_1 <= pages_1: 
                # https://webapi.bps.go.id/v1/api/list/model/th/lang/ind/domain/7600/var/491/page/1/key/70b9771878b76e68902b2aa1dffb2084/
                url_ = f"{BASE_URL}/list/model/th/lang/ind/domain/{DOMAIN}/var/{item_var['val']}/page/{page_1}/key/{API_KEY}/"
                while True: 
                    try:
                        response = requests.get(url_).json()
                        # print(response)
                        if response['status'] == 'OK':
                            tahun_arr.extend(response['data'][1])
                            pages_1 = response['data'][0]['pages']
                            break
                        elif response['status'] == 'Error':
                            print(response)
                            break
                    except Exception as e:
                        print(e)
                page_1 += 1
            # print(tahun_arr)
            for item_tahun in tahun_arr:
                #https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/7600/var/491/th/109;110/key/70b9771878b76e68902b2aa1dffb2084/
                url__ = f"{BASE_URL}/list/model/data/lang/ind/domain/{DOMAIN}/var/{item_var['val']}/th/{item_tahun['th_id']}/page/{page_1}/key/{API_KEY}/"
                while True: 
                    try:
                        response = requests.get(url__).json()
                        # print(response)
                        if response['status'] == 'OK':
                            response_arr.append(response)
                            break
                        elif response['status'] == 'Error':
                            print(response)
                            break
                    except Exception as e:
                        print(e)

        return response_arr    
    elif type == 3:
        response_arr = []
        index = 0
        for item_year in year_arr:
            """Mengambil semua subjek (CSA) yang tersedia"""
            url = f"{BASE_URL}/view/model/tablestatistic/domain/{DOMAIN}/year/{item_year}/lang/ind/id/{id}/key/{API_KEY}/"
            # print(url)
            while True: 
                try:
                    response = requests.get(url).json()
                    # print(response)
                    if response['status'] == 'OK':
                        response_arr.append(response)
                        break
                    elif response['status'] == 'Error':
                        print(response)
                        break
                except Exception as e:
                    print(e)
               

            if index == 0 and response is not None and response['status'] == 'OK':
                if "list_tahun_data" in response['data'][1]:
                    for item_avail_year in  response['data'][1]['list_tahun_data']:
                        if int(item_avail_year) not in year_arr :
                            year_arr.append(int(item_avail_year))
            index += 1
        return response_arr    
            
def json_to_text_2(item_table, json_data: dict, kategori, subyek, id_, metadata_) -> str:
    variabel = {str(item['val']): item['label'] for item in json_data.get('var', [])}
    turunan_variabel = {str(item['val']): item['label'] for item in json_data.get('turvar', [])}
    # Membersihkan tag HTML (seperti <b>) pada label wilayah/vervar
    vertical_variabel = {str(item['val']): item['label'].replace('<b>', '').replace('</b>', '') for item in json_data.get('vervar', [])}
    tahun = {str(item['val']): item['label'] for item in json_data.get('tahun', [])}
    turunan_tahun = {str(item['val']): item['label'] for item in json_data.get('turtahun', [])}
    
    data_content = json_data.get('datacontent', {})
    
    rows_text =[]

    # 2. Iterasi untuk merangkai kombinasi key dan mencocokkan dengan datacontent
    for item in json_data.get('var', []):
        var_val = item['val']
        var_label = item['label']
        rows_text.append('Variabel : '+ var_label+ ': ')
        for turvar_val, turvar_label in turunan_variabel.items():
            for v_val, v_label in vertical_variabel.items():
                for thn_val, thn_label in tahun.items():
                    for turthn_val, turthn_label in turunan_tahun.items():
                        if turthn_label.lower().strip() == 'tahun' :
                            turthn_label = ""
                        if thn_label.lower().strip() == 'tahun' :
                            thn_label = ""

                        if turvar_label.lower().strip() == 'tidak ada' and  len(turunan_variabel.items()) == 1:
                            turvar_label = ""
                        
                        # BPS menggabungkan value ID untuk membuat key pada datacontent
                        key = f"{v_val}{var_val}{turvar_val}{thn_val}{turthn_val}"
                        
                        # Jika kombinasi key ada di dalam data content, ambil nilainya
                        if key in data_content:
                            nilai = data_content[key]
                            if turvar_label == "" :
                                rows_text.append(f"- {v_label}, {thn_label} {turthn_label} : {nilai}")
                            else :
                                rows_text.append(f"- {v_label}, {thn_label} {turthn_label} -> {turvar_label} : {nilai}")
        if item['note'].strip() != '':
            rows_text.append("Catatan : "+item['note'])
        rows_text.append("")
                            
    output = []
    output.append(f"JUDUL: {item_table["title"]}")
    output.append(f"KATEGORI: {kategori}")
    output.append(f"SUBYEK: {subyek}")
    output.append(f"TAHUN: {json_data.get('tahun', [])[0]['label']}")
    output.append("\n")
    output.extend(rows_text)
    output.append("\n")


    id_ = id_ +'-'+ str(json_data.get('tahun', [])[0]['label'])
    metadata_['tahun'] = str(json_data.get('tahun', [])[0]['label'])
    
    return id_, "\n".join(output), metadata_



def json_to_text_3(item_table, json_data: dict, kategori, subyek, id_, metadata_) -> str:    
    """
    Mengonversi JSON data BPS menjadi teks narasi yang mudah dibaca.
    """
    # Navigasi ke main content (indeks 1 biasanya berisi data tabel)
    main_content = json_data['data'][1]
    
    # 1. Bersihkan Judul dan Metadata
    def clean_text(text):
        if not text: return ""
        # Unescape HTML entities (seperti &lt;) dan hapus tag HTML (seperti <sup>)
        text = html.unescape(text)
        return re.sub(r'<[^>]*>', '', text).strip()

    judul = clean_text(main_content.get('judul_tabel', 'Tabel Tanpa Judul'))
    tahun = main_content.get('tahun_data', '-')
    wilayah = main_content.get('wilayah', '-')
    sumber = clean_text(main_content.get('sumber', '-'))
    
    # 2. Identifikasi Kolom/Variabel
    # Map key kolom ke nama variabelnya
    kolom_map = {}
    for key, info in main_content['kolom'].items():
        kolom_map[key] = info['nama_variabel']
    
    # 3. Proses Data Baris
    rows_text = []
    for item in main_content['data']:
        label = item['label_raw']
        var_values = []
        
        if isinstance(item['variables'], dict):
            for var_key, var_data in item['variables'].items():
                nama_var = kolom_map.get(var_key, "Data")
                nilai = var_data['value']
                if item['satuan'] is not None :
                    nilai = var_data['value'] + item['satuan']
                var_values.append(f"{nama_var}: {nilai}")
        else :
            print("BUKAN DICT "+main_content.get('judul_tabel', 'Tabel Tanpa Judul'))

        
        rows_text.append(f"- {label} -> " + ", ".join(var_values))
    
    # 4. Susun Output Akhir
    output = []
    output.append(f"JUDUL: {judul}")
    output.append(f"WILAYAH: {wilayah}")
    output.append(f"KATEGORI: {kategori}")
    output.append(f"SUBYEK: {subyek}")
    output.append(f"TAHUN: {tahun}")
    output.append("\n")
    output.extend(rows_text)
    output.append("\n")
    output.append(f"SUMBER: {sumber}")

    id_ = id_ +'-'+ str(tahun)
    metadata_['tahun'] = str(tahun)
    
    return id_, "\n".join(output), metadata_

def populate_table():

    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=get_embedding_function() # Pastikan fungsi ini ada
    )

    pattern_data = """"Judul tabel: {judul}
Kategori: {kategori}.
Subyek: {subyek}.
Cakupan waktu: {awal} sampai {akhir}.
Jenis sumber: {sumber}."""

    categories = get_categories()
    
    for cate in categories:
        print("cate : "+cate["title"])
        page_1 = 1
        pages_1 = 1 
        while page_1 <= pages_1: 
            subject_a, pages_1 = get_subjects(cate['subcat_id'], page_1)
            for subjec in subject_a:
                ids=[]
                documents=[]
                print("subjec : "+subjec["title"])
                page_2 = 1
                pages_2 = 1 
                while page_2 <= pages_2:            
                    tables, pages_2_ = get_table(subjec['sub_id'], page_2)
                    if pages_2_ is not None :
                        pages_2 = pages_2_
                    for item in tables :
                        # print(item["title"])
                        # if item['id'] == 'Mjk0IzI=':
                        #     mulai = True
                        # if not mulai:
                        #     continue
                        tablesource = ""
                        if item['tablesource'] == '1':
                            tablesource = "Static Table"
                        elif item['tablesource'] == '2':
                            tablesource = "Dynamic Table"
                        elif item['tablesource'] == '3':
                            tablesource = "SIMDASI"

                        if item['tablesource'] == '1':
                            ids.append(str(cate['subcat_id'])+'-'+str(subjec['sub_id'])+'-'+str(item['id']))
                            documents.append(Document(page_content=pattern_data.format(
                                judul=item["title"],
                                kategori=cate["title"],
                                subyek=subjec["title"],
                                awal=item["oldest_period"],
                                akhir=item["latest_period"],
                                sumber=tablesource,
                            ), metadata={
                                'tipe': "tablestatistic",
                                'judul': item["title"],
                                'subcat_id': cate['subcat_id'],
                                'sub_id': subjec['sub_id'],
                                'table_id' : item['id'],
                                'sumber': item['tablesource']
                            }))

                        if item['tablesource'] == '2':
                            if item["oldest_period"] is None and item["latest_period"] is None:
                                continue
                            datas = get_detail_table(item['id'], 2, list(range(int(item["oldest_period"]), int(item["latest_period"])+1)))
                            for item_datas in datas:
                                id_, page_content_, metadata_ = json_to_text_2(item, item_datas, cate["title"], subjec["title"], 
                                                                                str(cate['subcat_id'])+'-'+str(subjec['sub_id'])+'-'+str(item['id']), 
                                                                               {
                                                                                    'tipe': "tablestatistic",
                                                                                    'judul': item["title"],
                                                                                    'subcat_id': cate['subcat_id'],
                                                                                    'sub_id': subjec['sub_id'],
                                                                                    'table_id' : item['id'],
                                                                                    'sumber': item['tablesource']
                                                                                })  
                                # print(id_)
                                # print(page_content_)
                                # print(metadata_)
                                ids.append(id_)
                                documents.append(Document(page_content=page_content_, metadata=metadata_))
                        if item['tablesource'] == '3':
                            if item["oldest_period"] is None and item["latest_period"] is None:
                                continue
                            datas = get_detail_table(item['id'], 3, list(range(int(item["oldest_period"]), int(item["latest_period"])+1)))
                            for item_datas in datas:
                                id_, page_content_, metadata_ = json_to_text_3(item, item_datas, cate["title"], subjec["title"], 
                                                                               str(cate['subcat_id'])+'-'+str(subjec['sub_id'])+'-'+str(item['id']), 
                                                                               {
                                                                                    'tipe': "tablestatistic",
                                                                                    'judul': item["title"],
                                                                                    'subcat_id': cate['subcat_id'],
                                                                                    'sub_id': subjec['sub_id'],
                                                                                    'table_id' : item['id'],
                                                                                    'sumber': item['tablesource']
                                                                                })  
                                # print(id_)
                                # print(page_content_)
                                # print(metadata_)
                                ids.append(id_)
                                documents.append(Document(page_content=page_content_, metadata=metadata_))


                       
                    page_2 += 1
                print(len(ids))
                print(len(documents))
                print(len(ids) == len(set(ids)))
                if len(ids) > 0:
                    db.add_documents(
                        documents,
                        ids=ids,
                    )
            page_1 += 1
            time.sleep(3)