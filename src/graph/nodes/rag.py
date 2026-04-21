from src.graph.rag.retriever import get_rag_data, get_rag_data_table
from src.graph.text import LLM_PROMPT
from src.graph.llm import llm_query
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv()) 

ai_disclaimen = "*AI dapat membuat kesalahan"

def data_or_analysis_router(state):
    history = "\n".join(item for item in state["chat_history"] if item.startswith("user"))
    new_chat = "\n".join(state["new_chat"])

    prompt = f"""
    Klasifikasikan pertanyaan user:

    DATA → mencari tabel, dataset, angka, link data
    ANALYSIS → meminta penjelasan, tren, penyebab, interpretasi

    Riwayat percakapan:
    {history}

    Pertanyaan: {new_chat}

    Jawab Hanya: data / analysis /keduanya
    """

    state["rag_type"] = llm_query(prompt, os.getenv('Whatsapp7600_04_Api_KEY')).strip()
    # print(state["rag_type"])
    return state

def rag_rewrite_query(state):
    # print("rag_rewrite_query")
    history = "\n".join(item for item in state["chat_history"] if item.startswith("user"))

    new_chat = "\n".join(state["new_chat"])

    prompt = f"""
Tugas: Ubah percakapan berikut menjadi pertanyaan mandiri untuk kebutuhan retrieval data.

Riwayat percakapan:
{history}

Pertanyaan baru:
Q:{new_chat}

Aturan:

1. Gabungkan konteks riwayat dan pertanyaan baru menjadi satu pertanyaan mandiri yang lengkap dan jelas.
2. Jika tidak ada tahun spesifik, tambahkan tahun terbaru (2026).
    Contoh: “pada tahun 2026”
3. Jika tidak ada lokasi spesifik, tambahkan Sulawesi Barat.
    Contoh: “di Sulawesi Barat”
4. Jika pertanyaan masih bersifat umum, buat menjadi spesifik dan sangat rinci.
5. Jangan mengulang instruksi, jangan meminta konfirmasi, dan jangan menambahkan penjelasan.

Output:
Pertanyaan mandiri.
"""
    # print(history)
    # print(state["new_chat"])
    state["rag_query"] = llm_query(prompt, os.getenv('Whatsapp7600_02_Api_KEY'))
    print(state["rag_query"])
    return state

def rag_search(state):
    # print("rag_search")

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
        judul_ =[]
        for doc, _score in docs_table :
            url_.append('https://sulbar.bps.go.id/id/statistics-table/'+doc.metadata.get("sumber", None)+'/'+doc.metadata.get("table_id", None)+'/data.html')
            judul_.append(doc.metadata.get("judul", None))
        state["rag_table_url"] = url_
        state["rag_table_judul"] = judul_
        return state

def rag_answer(state):
    # print("rag_answer")

    if state["rag_type"].lower() == 'data' :
        if len(state["rag_table_judul"]) == 0 :
            state["answer"] = ["Maaf, kami belum menemukan data yang sesuai."]
        else :
            text = "Berikut daftar data yang kami temukan:\n\n"
            for i, item in enumerate(state["rag_table_url"]):
                title = state["rag_table_judul"][i]
                url = state["rag_table_url"][i]
                text += f"{i+1}. {title}\n   {url}\n\n"
            state["answer"] = [text, ai_disclaimen]
        return state
    elif state["rag_type"].lower() == 'analysis' :
        new_chat = "\n".join(state["new_chat"])
        prompt = LLM_PROMPT.format(
            context=state["rag_context_pdf"],
            question=new_chat
        )
        state["answer"] = [llm_query(prompt,  os.getenv('Whatsapp7600_03_Api_KEY')), ai_disclaimen]
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
            state["answer"] = [text[:-4]]

        if text == "" :
            state["answer"] = [llm_query(prompt,  os.getenv('Whatsapp7600_03_Api_KEY')), ai_disclaimen]
        else :
            state["answer"] = [llm_query(prompt,  os.getenv('Whatsapp7600_03_Api_KEY')), text, ai_disclaimen]
        return state
       