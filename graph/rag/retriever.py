from graph.rag.chroma_client import get_vectorstore_pdf, get_vectorstore_table

def get_rag_data_arr(query_text_arr, k_=10):
    db = get_vectorstore_pdf()
    results_arr = []
    for item_query in query_text_arr:
        results = db.similarity_search_with_score(item_query, k=k_)
        results_arr.extend(results)
    return results_arr

def get_content_rag_data_by_halaman(source, page):
    db = get_vectorstore_pdf()
    result = db.get(where={
        "$and": [
            {"source": source},
            {"page": page}
        ]
    } )

    content_full = ""
    for item in result : 
        content_full +="\n"+item.page_content
    return content_full


def get_rag_data_table_arr(query_text_arr, k_=10):
    db = get_vectorstore_table()
    results_arr = []
    for item_query in query_text_arr:
        results = db.similarity_search_with_score(item_query, k=k_)
        results_arr.extend(results)
    return results_arr