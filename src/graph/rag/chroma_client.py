from langchain_chroma import Chroma
from src.get_embedding_function import get_embedding_function
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv()) 

def get_vectorstore():
    return Chroma(persist_directory=os.getenv('CHROMA_PATH'), embedding_function=get_embedding_function())