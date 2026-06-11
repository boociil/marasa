from langchain_ollama import OllamaEmbeddings
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv()) 

def get_embedding_function():
    # URL default Ollama adalah http://localhost:11434
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    return OllamaEmbeddings(
        model="nomic-embed-text-v2-moe",
        base_url=ollama_url
    )
