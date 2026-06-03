from graph.rag.chroma_client import get_vectorstore_pdf, get_vectorstore_table
from _logger import logger

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

def get_rag_data_arr(query_text_arr, k_=10):    
    db = get_vectorstore_pdf()
    results_arr = []
    for item_query in query_text_arr:
        results = db.similarity_search_with_score(item_query, k=k_, where_document=search_filter)
        results_arr.extend(results)
    return results_arr

def get_content_rag_data_by_halaman(source, page):
    db = get_vectorstore_pdf()
    result = db.get(where={
        "$and": [
            {"source": source},
            {"page": page}
        ]
    }, where_document=search_filter )

    page_contents = result.get("documents", [])

    content_full = ""
    for item in page_contents : 
        content_full +="\n"+item

    return content_full


def get_rag_data_table_arr(query_text_arr, k_=10):
    db = get_vectorstore_table()
    results_arr = []
    for item_query in query_text_arr:
        results = db.similarity_search_with_score(item_query, k=k_)
        results_arr.extend(results)
    return results_arr