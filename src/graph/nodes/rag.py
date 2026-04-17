from google import genai
from src.graph.rag.retriever import get_rag_data
from src.graph.text import LLM_PROMPT
from dotenv import load_dotenv, find_dotenv
from google import genai
import os

load_dotenv(find_dotenv()) 

CHROMA_PATH = os.getenv('CHROMA_PATH')
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def rag_rewrite_query(state):
    history = "\n".join(state["chat_history"])
    new_chat = "\n".join(state["new_chat"])
    prompt = f"Ubah menjadi pertanyaan mandiri:\n{history}\nQ:{new_chat} \n jika tidak ada tahun spesifik masukkan tahun terbaru (contoh : pada tahun 2026) \n jika tidak ada lokasi spesifik masukkan sulawesi barat (contoh : di sulawesi barat)"

    while True:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", contents=prompt
        )

        if response and response.text:
            state["rag_query"] = response.text
            return state


def rag_search(state):
    docs = get_rag_data(state["rag_query"])
    state["rag_context"] = "\n\n".join([d.page_content for d in docs])
    return state

def rag_answer(state):
    prompt = LLM_PROMPT.format(
        context=state["rag_context"],
        question=state["message"]
    )

    while True:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", contents=prompt
        )

        if response and response.text:
            state["answer"] = response.text
            return state