from _global import vectorstore_isi_pdf, vectorstore_table, vectorstore_rilis_publikasi
import asyncio
from langchain_community.tools import DuckDuckGoSearchResults
from db.model_rag import DDGS, RagData, RagPublikasiBRS, RagRilisPublikasi
import uuid
import os
from _global import logger, BASE_DIR
from pathlib import Path
import aiohttp
from bs4 import BeautifulSoup

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
                    content = doc.page_content, 
                    score= 1
                )
            )
        
    return return_value

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
