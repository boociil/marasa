from langchain_chroma import Chroma
from populate.get_embedding_function import get_embedding_function
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv()) 

def get_vectorstore_pdf():
    return Chroma(persist_directory=os.getenv('CHROMA_PATH_ISI_PDF'), embedding_function=get_embedding_function())

def get_vectorstore_table():
    return Chroma(persist_directory=os.getenv('CHROMA_PATH_TABLE'), embedding_function=get_embedding_function())