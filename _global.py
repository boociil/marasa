from langchain_chroma import Chroma
from populate.get_embedding_function import get_embedding_function
from dotenv import load_dotenv, find_dotenv
from diskcache import Cache
import chromadb
from loguru import logger
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "log")

load_dotenv(find_dotenv()) 

def get_vectorstore_pdf():
    CHROMA_HOST = "localhost"
    CHROMA_PORT = int(os.getenv("CHROMA_PORT_ISI_PDF", 8090))

    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    return Chroma(
        client=chroma_client,
        embedding_function=get_embedding_function() 
    )


def get_vectorstore_table():
    CHROMA_HOST = "localhost"
    CHROMA_PORT = int(os.getenv("CHROMA_PORT_TABLE", 8091))

    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    return Chroma(
        client=chroma_client,
        embedding_function=get_embedding_function() 
    )

def get_vectorstore_rilis_publikasi():
    CHROMA_HOST = "localhost"
    CHROMA_PORT = int(os.getenv("CHROMA_PORT_RILIS_PUBLIKASI", 8092))

    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    return Chroma(
        client=chroma_client,
        embedding_function=get_embedding_function() 
    )


vectorstore_isi_pdf = get_vectorstore_pdf()
vectorstore_table = get_vectorstore_table()
vectorstore_rilis_publikasi = get_vectorstore_rilis_publikasi()

logger.add(
    os.path.join(LOG_DIR, "api_{time:YYYY-MM-DD}.log"), # Nama file akan jadi seperti log/api_2026-05-26.log
    rotation="00:00",                # Buat file baru setiap jam 12 malam (tengah malam)
    retention="30 days",             # Opsional: Otomatis hapus file log yang lebih tua dari 30 hari
    level="INFO"
)

shared_cache = Cache("cache/share")
session_in_works = Cache("cache/session_in_works")
web_api_cache = Cache("cache/web_api")