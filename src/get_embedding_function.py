from langchain_ollama import OllamaEmbeddings


def get_embedding_function():
    ## nomic-embed-text-v2-moe
    ## nomic-embed-text
    embeddings = OllamaEmbeddings(model="nomic-embed-text-v2-moe")
    return embeddings
