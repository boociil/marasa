from langchain_chroma import Chroma
from src.get_embedding_function import get_embedding_function

CHROMA_PATH = "chroma"

def get_vectorstore():
    return Chroma(persist_directory=CHROMA_PATH, embedding_function=get_embedding_function())