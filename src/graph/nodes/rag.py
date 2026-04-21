from src.graph.rag.retriever import get_rag_data, get_rag_data_table
from src.graph.text import LLM_PROMPT
from src.graph.llm import llm_query
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv()) 


def data_or_analysis_router(state):
    new_chat = "\n".join(state["new_chat"])

    prompt = f"""
    Klasifikasikan pertanyaan user:

    DATA → mencari tabel, dataset, angka, link data
    ANALYSIS → meminta penjelasan, tren, penyebab, interpretasi

    Pertanyaan: {new_chat}

    Jawab Hanya: data / analysis /keduanya
    """

    state["rag_type"] = llm_query(prompt, os.getenv('Whatsapp7600_04_Api_KEY')).strip()
    print(state["rag_type"])
    return state

def rag_rewrite_query(state):
    print("rag_rewrite_query")
    history = "\n".join(state["chat_history"])
    new_chat = "\n".join(state["new_chat"])

    prompt = f"""
Ubah menjadi pertanyaan mandiri untuk retrival data  :
{history}

Q:{new_chat}

jika tidak ada tahun spesifik masukkan tahun terbaru (contoh : pada tahun 2026)
jika tidak ada lokasi spesifik masukkan sulawesi barat (contoh : di sulawesi barat)

jika pertanyaan dibuat secara umum buat rinciannya 

tahun terbaru saat ini 2026

langsug berikan pertanyaa mandirinya jangan mengulang dan bertanya ulang
"""
    
    state["rag_query"] = llm_query(prompt, os.getenv('Whatsapp7600_02_Api_KEY'))
    print(state["rag_query"])
    return state

def rag_search(state):
    print("rag_search")

    if state["rag_type"].lower() == 'data' :
        docs_table = get_rag_data_table(state["rag_query"])
        url_ = []
        judul_ =[]
        for doc, _score in docs_table :
            url_.append('https://sulbar.bps.go.id/id/statistics-table/'+doc.metadata.get("sumber", None)+'/'+doc.metadata.get("table_id", None)+'/data.html')
            judul_.append(doc.metadata.get("judul", None))
        state["rag_table_url"] = url_
        state["rag_table_judul"] = judul_
        return state
    elif state["rag_type"].lower() == 'analysis' :
        docs_pdf = get_rag_data(state["rag_query"])
        state["rag_context_pdf"] = "\n\n---\n\n".join([doc.page_content for doc, _score in docs_pdf])
        return state
    else :
        docs_pdf = get_rag_data(state["rag_query"])
        state["rag_context_pdf"] = "\n\n---\n\n".join([doc.page_content for doc, _score in docs_pdf])

        docs_table = get_rag_data_table(state["rag_query"])
        url_ = []
        for doc, _score in docs_table :
            url_.append('https://sulbar.bps.go.id/id/statistics-table/'+doc.metadata.get("sumber", None)+'/'+doc.metadata.get("table_id", None)+'/data.html')
        state["rag_table_url"] = url_
        state["rag_table_judul"] = [doc.page_content for doc, _score in docs_table]
        return state

def rag_answer(state):
    print("rag_answer")

    if state["rag_type"].lower() == 'data' :
        if len(state["rag_table_judul"]) == 0 :
            state["answer"] = ["Maaf, kami belum menemukan data yang sesuai."]
        else :
            text = "Berikut daftar data yang kami temukan:\n\n"
            for i, item in enumerate(state["rag_table_url"]):
                title = state["rag_table_judul"][i]
                url = state["rag_table_url"][i]
                text += f"{i+1}. {title}\n   {url}\n\n"
            state["answer"] = [text]
        return state
    elif state["rag_type"].lower() == 'analysis' :
        new_chat = "\n".join(state["new_chat"])
        prompt = LLM_PROMPT.format(
            context=state["rag_context_pdf"],
            question=new_chat
        )
        state["answer"] = [llm_query(prompt,  os.getenv('Whatsapp7600_03_Api_KEY'))]
        return state
    else :
        new_chat = "\n".join(state["new_chat"])
        prompt = LLM_PROMPT.format(
            context=state["rag_context_pdf"],
            question=new_chat
        )
        
        text = ""
        if len(state["rag_table_judul"]) > 0 :
            text = "Berikut daftar data yang kami temukan:\n\n"
            for i, item in enumerate(state["rag_table_url"]):
                title = state["rag_table_judul"][i]
                url = state["rag_table_url"][i]
                text += f"{i+1}. {title}\n   {url}\n\n"
            state["answer"] = [text]

        if text == "" :
            state["answer"] = [llm_query(prompt,  os.getenv('Whatsapp7600_03_Api_KEY'))]
        else :
            state["answer"] = [llm_query(prompt,  os.getenv('Whatsapp7600_03_Api_KEY')), text]
        return state
       