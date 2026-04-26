from src.graph.rag.chroma_client import get_vectorstore_pdf, get_vectorstore_table

def get_rag_data(query_text):
    db = get_vectorstore_pdf()

    results = db.similarity_search_with_score(query_text, k=10)
    return results
    # results = db.imilarity_search_with_score(query_text, k=10)

    # filtered_docs_with_scores = [
    #     (doc, score) 
    #     for doc, score in results
    #     if score <= 0.75
    # ]

    # return filtered_docs_with_scores

def get_rag_data_table(query_text):
    db = get_vectorstore_table()

    results = db.similarity_search_with_score(query_text, k=10)
    return results
    # results = db.imilarity_search_with_score(query_text, k=10)

    # filtered_docs_with_scores = [
    #     (doc, score) 
    #     for doc, score in results
    #     if score <= 0.75
    # ]

    # return filtered_docs_with_scores