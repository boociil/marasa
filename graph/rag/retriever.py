from _global import vectorstore_isi_pdf, vectorstore_table, vectorstore_rilis_publikasi
import asyncio
from langchain_community.tools import DuckDuckGoSearchResults
from db.model_rag import DDGS, RagData, RagPublikasiBRS, RagRilisPublikasi
import httpx
import uuid
import os
from _global import logger, BASE_DIR, web_api_cache
from pathlib import Path
import aiohttp
from bs4 import BeautifulSoup
import os, re, html
from dotenv import load_dotenv, find_dotenv
from graph.nodes.rerank import GLOBAL_KEY_POOL, fetch_chunk_jawaban, append_chunk

load_dotenv(find_dotenv())
API_KEY = os.getenv("API_BPS")
DOMAIN = "7600"
BASE_URL = "https://webapi.bps.go.id/v1/api"

search_filter = {
"$and": [
        {"$not_contains": "daftar isi"},
        {"$not_contains": "Daftar Isi"},
        {"$not_contains": "DAFTAR ISI"},
        
        {"$not_contains": "daftar tabel"},
        {"$not_contains": "Daftar Tabel"},
        {"$not_contains": "DAFTAR TABEL"},
        
        {"$not_contains": "daftar gambar"},
        {"$not_contains": "Daftar Gambar"},
        {"$not_contains": "DAFTAR GAMBAR"},

        {"$not_contains": "daftar pustaka"},
        {"$not_contains": "Daftar Pustaka"},
        {"$not_contains": "DAFTAR PUSTAKA"},
        {"$not_contains": "........"},
        {"$not_contains": "…………"},
        {"$not_contains": """Halaman
Page"""}
    ]
}

async def get_rag_data_arr(query_text_arr, keywords, k_=10):    
    tasks = [
        vectorstore_isi_pdf.amax_marginal_relevance_search(item_query, k=k_, fetch_k=(5*k_),lambda_mult=0.5, where_document=search_filter)
        for item_query in query_text_arr
    ]
    
    results_per_query = await asyncio.gather(*tasks)
    
    results_arr = []
    for results in results_per_query:
        results_arr.extend(results)

    sorce_page_unique = []
    return_value = []
    sorce_page_unique_halama = {}

    tasks2 = []
    for doc in results_arr:
        tasks2.append(get_content_rag_data_by_halaman(doc.metadata['source'], doc.metadata['page']))
    if len(tasks2) > 0 :
        results_per_query_halaman = await asyncio.gather(*tasks2)
        for item_ in results_per_query_halaman :
            sorce_page_unique_halama[item_[0]] = item_[1]     
                                                                   
    for doc in results_arr:
        bps_id = ""
        type = ""

        path_folder = str(doc.id).split(":")[0]
        if path_folder.endswith(".pdf"):
            path_folder = path_folder[:-4]
        path_image = os.path.join(BASE_DIR, path_folder,str(int(doc.metadata['page'])+1)+'.jpg')
        path_image = path_image.replace("/PDF_ALL/","/IMAGES/")
        path_image = str(Path(path_image.replace("\\", "/")))

        if 'pub_id' in doc.metadata : 
            bps_id = doc.metadata['pub_id']
            type = 'pub'
        if 'brs_id' in doc.metadata : 
            bps_id = doc.metadata['brs_id']
            type = 'brs'
        
        source_page = f"{doc.metadata['source'] } -+- {doc.metadata['page']}"
        text = doc.page_content
        if any(keyword.lower() in text.lower() for keyword in keywords):
            if source_page not in sorce_page_unique :
                return_value.append(
                    RagPublikasiBRS( 
                        id = str(uuid.uuid4()),
                        bps_id = str(bps_id),
                        type = type,
                        title = doc.metadata['title'], 
                        halaman= int(doc.id.split(':')[-2])+1, 
                        content = doc.page_content if source_page not in sorce_page_unique_halama else sorce_page_unique_halama[source_page], 
                        rl_date = doc.metadata['rl_date'], 
                        file_path = path_image,
                        score= 1
                    )
                )
                sorce_page_unique.append(source_page)
        
    return return_value

async def get_content_rag_data_by_halaman(source, page):
    result = await asyncio.to_thread(
        vectorstore_isi_pdf.get,
        where={
            "$and": [
                {"source": source},
                {"page": page}
            ]
        }, 
        where_document=search_filter  # Pass parameters as standard keyword arguments
    )

    page_contents = result.get("documents", [])

    content_full = ""
    for item in page_contents : 
        content_full +="\n"+item

    return [f"{source} -+- {page}", content_full]


async def get_rag_data_table_arr(query_text_arr, keywords, k_=10):
    tasks = [
        vectorstore_table.amax_marginal_relevance_search(item_query, k=k_, fetch_k=(5*k_),lambda_mult=0.5, where_document=search_filter)
        for item_query in query_text_arr
    ]
    
    results_per_query = await asyncio.gather(*tasks)
    
    results_arr = []
    for results in results_per_query:
        results_arr.extend(results)

    return_value = []
    for doc in results_arr:
        text = doc.page_content
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return_value.append(
                RagData( 
                    id = str(uuid.uuid4()),
                    judul = doc.metadata['judul'], 
                    url= 'https://sulbar.bps.go.id/id/statistics-table/'+doc.metadata.get("sumber", None)+'/'+doc.metadata.get("table_id", None)+'/data.html', 
                    sumber=doc.metadata.get("sumber", 0),
                    table_id=f"{doc.metadata.get("table_id", None)}",
                    content = doc.page_content, 
                    score= 1
                )
            )
        
    return return_value

async def get_content_rag_data_table_tahun(ques, judul, sumber, table_id , keyword = []):
    year_arr= sorted([
        int(x) for x in keyword
        if (
            isinstance(x, int) and 1900 <= x <= 2100
        ) or (
            isinstance(x, str) and x.isdigit() and 1900 <= int(x) <= 2100
        )
    ])

    ar_data = []

    async with httpx.AsyncClient() as client:
        datas = await get_detail_table(client, table_id, int(sumber), year_arr)
        if f"{sumber}" == '2':
            for item_datas in datas:
                ar_data.append(json_to_text_2(judul, item_datas))
        elif f"{sumber}" == '3':
            for item_datas in datas:
                ar_data.append(json_to_text_3(judul, item_datas))
    
    chunks_arr = []
    chunks = ""

    for item_data in ar_data :
        chunks = append_chunk(chunks_arr, chunks, item_data)

    if chunks:
        chunks_arr.append(chunks)

    key_pool = GLOBAL_KEY_POOL
    
    tasks = [
        asyncio.create_task(fetch_chunk_jawaban(ques, c, key_pool))
        for c in chunks_arr
    ]

    jawaban_arr = await asyncio.gather(*tasks)

    logger.info(jawaban_arr)

    return "\n".join(jawaban_arr)

async def get_rag_rilis_publikasi(query_text_arr, keywords, k_=10):
    tasks = [
        vectorstore_rilis_publikasi.asimilarity_search_with_score(item_query, k=k_, where_document=search_filter)
        for item_query in query_text_arr
    ]
    
    results_per_query = await asyncio.gather(*tasks)
    
    results_arr = []
    for results in results_per_query:
        results_arr.extend(results)

    return_value = []
    for doc, _score in results_arr:
        text = doc.page_content
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return_value.append(
                RagRilisPublikasi( 
                    id = str(uuid.uuid4()),
                    tipe = doc.metadata['tipe'], 
                    bps_id  = str(doc.metadata['id']), 
                    rl_date = doc.metadata['rl_date'], 
                    content = doc.page_content, 
                    score= _score
                )
            )
        
    return return_value

async def get_ddgs_arr(query):
    gagal = 0
    while True:
        if gagal == 2 :
            return []
        try :
            search = DuckDuckGoSearchResults(output_format="list")
            logger.info(f"site:bps.go.id {', '.join(query)}")
            results_list = await search.ainvoke(f"site:bps.go.id {', '.join(query)}")
            return_value = []
            async with aiohttp.ClientSession() as session:
                fetch_tasks = [fetch_web_content(session, res['link']) for res in results_list]
                web_contents = await asyncio.gather(*fetch_tasks)
            
            for res, content in zip(results_list, web_contents):
            
                final_text = content if content.strip() != "" else res['snippet']
                return_value.append(
                    DDGS( 
                        id = str(uuid.uuid4()),
                        snippet = final_text, # Snippet sekarang berisi data lengkap website!
                        title = res['title'],
                        link = res['link'],
                    )
                )
            return return_value
        except Exception as e:
            logger.info(e)
            gagal += 1
            await asyncio.sleep(2)

async def fetch_web_content(session, url):
    try:
        # Gunakan timeout agar tidak hang jika website lambat
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Hapus elemen script dan style agar teks bersih
                for script in soup(["script", "style"]):
                    script.extract()
                    
                text = soup.get_text(separator=' ', strip=True)
                
                # Batasi teks agar tidak menguras token LLM secara ekstrem (misal max 4000 karakter)
                return text[:4000]
    except Exception as e:
        logger.error(f"Gagal mengambil data dari {url}: {e}")
    return "" # Kembalikan string kosong jika gagal

async def get_detail_table(client, id , type = 0, year_arr = []):
    if len(year_arr) == 0 :
        """Mengambil semua subjek (CSA) yang tersedia"""
        url = f"{BASE_URL}/view/model/tablestatistic/domain/{DOMAIN}/lang/ind/id/{id}/key/{API_KEY}/"
        
        attempt = 1
        while True: 
            if attempt > 4:
                logger.error(f"Gagal mengambil data CSA setelah 4 percobaan: {url}")
                return []
            
            try:
                response = web_api_cache.get(url)
                if response is not None:
                    if response['status'] == 'OK':
                        return response
                response = (await client.get(url)).json()
                
                if response['status'] == 'OK':
                    web_api_cache.set(url, [response], 15*60)
                    return [response]
                elif response['status'] == 'Error':
                    logger.info(response)
                    return []
            except Exception as e:
                logger.info(e)
                await asyncio.sleep(2)
                attempt += 1
            
    elif type == 2:
        response_arr = []
        url = f"{BASE_URL}/view/model/tablestatistic/domain/{DOMAIN}/lang/ind/id/{id}/key/{API_KEY}/"
        vars_arr = []
        
        attempt = 1
        while True: 
            if attempt > 4:
                logger.error(f"Gagal mengambil variabel setelah 4 percobaan: {url}")
                break
                
            try:
                response = web_api_cache.get(url)
                if response is None:
                    response = (await client.get(url)).json()
                    if response['status'] == 'OK':
                        web_api_cache.set(url, response, 15*60)

                logger.info(response)
                
                if response['status'] == 'OK':
                    vars_arr = response['var']
                    break
                elif response['status'] == 'Error':
                    logger.info(response)
                    break
            except Exception as e:
                logger.info(e)
                await asyncio.sleep(2)
                attempt += 1

        for item_var in vars_arr :
            page_1 = 1
            pages_1 = 1 
            tahun_arr = []
            while page_1 <= pages_1: 
                url_ = f"{BASE_URL}/list/model/th/lang/ind/domain/{DOMAIN}/var/{item_var['val']}/page/{page_1}/key/{API_KEY}/"
                
                attempt_page = 1
                while True: 
                    if attempt_page > 4:
                        logger.error(f"Gagal mengambil page setelah 4 percobaan: {url_}")
                        break
                        
                    try:
                        # Perbaikan bug: Menggunakan url_, bukan url
                        response = web_api_cache.get(url_)
                        if response is None:
                            response = (await client.get(url_)).json()
                            if response['status'] == 'OK':
                                web_api_cache.set(url_, response, 15*60)
                        
                        if response['status'] == 'OK':
                            tahun_arr.extend(response['data'][1])
                            pages_1 = response['data'][0]['pages']
                            break
                        elif response['status'] == 'Error':
                            logger.info(response)
                            break
                    except Exception as e:
                        logger.info(e)
                        await asyncio.sleep(2)
                        attempt_page += 1
                page_1 += 1
                
            tahun_arr_ = []
            for item in tahun_arr :
                if item in year_arr:
                    tahun_arr_.append(item)
            
            for item_tahun in tahun_arr_:
                url__ = f"{BASE_URL}/list/model/data/lang/ind/domain/{DOMAIN}/var/{item_var['val']}/th/{item_tahun['th_id']}/page/{page_1}/key/{API_KEY}/"
                
                attempt_data = 1
                while True: 
                    if attempt_data > 4:
                        logger.error(f"Gagal mengambil data tahun setelah 4 percobaan: {url__}")
                        break
                        
                    try:
                        # Perbaikan bug: Menggunakan url__, bukan url
                        response = web_api_cache.get(url__)
                        if response is None:
                            response = (await client.get(url__)).json()
                            if response['status'] == 'OK':
                                web_api_cache.set(url__, response, 15*60)
                        
                        if response['status'] == 'OK':
                            response_arr.append(response)
                            break
                        elif response['status'] == 'Error':
                            logger.info(response)
                            break
                    except Exception as e:
                        logger.info(e)
                        await asyncio.sleep(2)
                        attempt_data += 1

        return response_arr    
        
    elif type == 3:
        response_arr = []
        index = 0
        for item_year in year_arr:
            """Mengambil semua subjek (CSA) yang tersedia"""
            url = f"{BASE_URL}/view/model/tablestatistic/domain/{DOMAIN}/year/{item_year}/lang/ind/id/{id}/key/{API_KEY}/"
            
            attempt = 1
            response = None # Inisialisasi awal agar tidak error di pengecekan bawah
            while True: 
                if attempt > 4:
                    logger.error(f"Gagal mengambil data tahunan setelah 4 percobaan: {url}")
                    break
                    
                try:
                    response = web_api_cache.get(url)
                    if response is None:
                        response = (await client.get(url)).json()
                        if response['status'] == 'OK':
                            web_api_cache.set(url, response, 15*60)
                    
                    if response['status'] == 'OK':
                        response_arr.append(response)
                        break
                    elif response['status'] == 'Error':
                        logger.info(response)
                        break
                except Exception as e:
                    logger.info(e)
                    await asyncio.sleep(2)
                    attempt += 1
               
            # Gunakan dict.get agar lebih aman jika response ternyata None
            if index == 0 and response is not None and response.get('status') == 'OK':
                if "list_tahun_data" in response['data'][1]:
                    for item_avail_year in response['data'][1]['list_tahun_data']:
                        if int(item_avail_year) not in year_arr :
                            year_arr.append(int(item_avail_year))
            index += 1
            
        return response_arr
     

def json_to_text_2(judul: str, json_data: dict) -> str:
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
    output.append(f"JUDUL: {judul}")
    output.append(f"TAHUN: {json_data.get('tahun', [])[0]['label']}")
    output.append("\n")
    output.extend(rows_text)
    output.append("\n")

    
    return "\n".join(output)



def json_to_text_3(judul: str, json_data: dict) -> str:    
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
            logger.info("BUKAN DICT "+main_content.get('judul_tabel', 'Tabel Tanpa Judul'))

        
        rows_text.append(f"- {label} -> " + ", ".join(var_values))
    
    # 4. Susun Output Akhir
    output = []
    output.append(f"JUDUL: {judul}")
    output.append(f"WILAYAH: {wilayah}")
    output.append(f"TAHUN: {tahun}")
    output.append("\n")
    output.extend(rows_text)
    output.append("\n")
    output.append(f"SUMBER: {sumber}")
    
    return "\n".join(output)
        
