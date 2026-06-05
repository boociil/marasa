from _global import logger
from _global import vectorstore_isi_pdf, vectorstore_table
import asyncio


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
        {"$not_contains": """Halaman
Page"""}
    ]
}

async def get_rag_data_arr(query_text_arr, k_=10):    
    tasks = [
        vectorstore_isi_pdf.asimilarity_search_with_score(item_query, k=k_, where_document=search_filter)
        for item_query in query_text_arr
    ]
    
    results_per_query = await asyncio.gather(*tasks)
    
    results_arr = []
    for results in results_per_query:
        results_arr.extend(results)
        
    return results_arr

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

    return content_full


async def get_rag_data_table_arr(query_text_arr, k_=10):
    tasks = [
        vectorstore_table.asimilarity_search_with_score(item_query, k=k_, where_document=search_filter)
        for item_query in query_text_arr
    ]
    
    results_per_query = await asyncio.gather(*tasks)
    
    results_arr = []
    for results in results_per_query:
        results_arr.extend(results)
        
    return results_arr