from src.graph.rag.chroma_client import get_vectorstore
from src.get_embedding_function import get_embedding_function

def get_rag_data(query_text):
    db = get_vectorstore()

    results = db.similarity_search_with_score(query_text, k=10)
    # results = db.imilarity_search_with_score(query_text, k=10)

    return results