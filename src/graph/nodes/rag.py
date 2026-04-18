from src.graph.rag.retriever import get_rag_data
from src.graph.text import LLM_PROMPT
from src.graph.llm import llm_query
from dotenv import load_dotenv, find_dotenv
import os
import time

load_dotenv(find_dotenv()) 

CHROMA_PATH = os.getenv('CHROMA_PATH')

def rag_rewrite_query(state):
    print("rag_rewrite_query")
    history = "\n".join(state["chat_history"])
    new_chat = "\n".join(state["new_chat"])

    prompt = f"""
Ubah menjadi pertanyaan mandiri untuk retrival data di rag :
{history}

Q:{new_chat}

jika tidak ada tahun spesifik masukkan tahun terbaru (contoh : pada tahun 2026, info : tahun terbaru saat ini 2026)
jika tidak ada lokasi spesifik masukkan sulawesi barat (contoh : di sulawesi barat)

langsug berikan pertanyaa mandirinya jangan mengulang dan bertanya ulang
"""
    
    state["rag_query"] = llm_query(prompt, os.getenv('Whatsapp7600_02_Api_KEY'))
    print(state["rag_query"])
    return state
        


def rag_search(state):
    print("rag_search")
    docs = get_rag_data(state["rag_query"])
    print(docs)
    state["rag_context"] = "\n\n---\n\n".join([doc.page_content for doc, _score in docs])
    return state

def rag_answer(state):
    print("rag_answer")
    new_chat = "\n".join(state["new_chat"])
    prompt = LLM_PROMPT.format(
        context=state["rag_context"],
        question=new_chat
    )

    state["answer"] = [llm_query(prompt,  os.getenv('Whatsapp7600_03_Api_KEY'))]
    print(state["answer"])
    return state
       