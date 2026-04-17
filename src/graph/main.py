from langgraph.graph import StateGraph, START, END

from src.graph.state import BPSState
from src.graph.nodes.rag import rag_rewrite_query, rag_search, rag_answer
from src.graph.nodes.complaint import create_ticket
from src.graph.nodes.end_checker import end_checker
from src.graph.nodes.human_node import human_node
from src.graph.nodes.konsultasi import konsultasi
from src.graph.text import menu_bps, Form_Identitas

from src.graph.db.models import User, ChatSession, ChatMessage, Ticket, get_user_by_phone, get_or_create_active_session, load_last_messages

import re

FORM_PATTERNS = {
    "nama_lengkap": r"nama\s*lengkap\s*:\s*(.+)",
    "email": r"email\s*:\s*(.+)",
    "tahun_lahir": r"tahun\s*lahir\s*:\s*(\d{4})",
    "pekerjaan": r"pekerjaan\s*:\s*(.+)",
    "instansi": r"instansi.*?:\s*(.+)",
}

def extract_form_data(text: str):
    text_lower = text.lower()
    result = {}

    for field, pattern in FORM_PATTERNS.items():
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            result[field] = match.group(1).strip()

    return result

def main_chat(phoneNumber: str, name: str, text: list[str], isfromMe: bool): 
    session, baru_status = get_or_create_active_session(phoneNumber)
    if baru_status :
        return [menu_bps]
    elif session.layanan == 0 : 
        number = 0
        for item in text:
            if item in ['1','2','3','4','5'] :
                number = int(item)
        session.layanan = number
        session.save()

    if session.layanan == 0 :
        return []

    user = get_user_by_phone(phoneNumber)

    if user is None :
        check_iden = False
        extract_form = {}
        for item in text :
            if 'Nama Lengkap' in item :
                check_iden = True
                extract_form = extract_form_data(item)
        
        if not check_iden : 
            return [
                "Mohon mengisi form identitas untuk dokumentasi kami",
                Form_Identitas
            ]
        else :
            try :
                print(extract_form)
                user =  User.create(
                    nama = name,
                    notelp = phoneNumber,
                    email = extract_form['email'],
                    nama_lengkap = extract_form['nama_lengkap'],
                    pekerjaan = extract_form['pekerjaan'],
                    instansi = extract_form['instansi'],
                )
            except Exception as e:
                print(e)
                return [
                    "Mohon mengisi identitas dengan menyalin form dan mengisi bagian kanan titik dua"
                ]

    state = {
        "session_id": session.id,
        "session_done": False,
        "layanan_type": session.layanan,
        "need_human": False,
        "is_done": False,

        "nama": user.nama,
        "notelp": user.notelp,
        "nama_lengkap": user.nama_lengkap,
        
        "answer": [],
        "new_chat": text,
        "chat_history": load_last_messages(session)
    }

    builder = StateGraph(BPSState)
    # nodes
  
    builder.add_node("human_node", human_node)
    builder.add_node("konsultasi", konsultasi)
    builder.add_node("create_ticket", create_ticket)
    builder.add_node("rag_rewrite_query", rag_rewrite_query)
    builder.add_node("rag_search", rag_search)
    builder.add_node("rag_answer", rag_answer)
    builder.add_node("end_checker", end_checker)


    
    

    builder.add_edge(START, "end_checker")

    def followup_end_checker(state):
        return "human_node" if not state["is_done"] else END

    builder.add_conditional_edges("end_checker", followup_end_checker)

    def followup_human_node(state):
        if not state["need_human"] :
            match  state["layanan_type"] : 
                case 1 :
                    return "konsultasi"
                case 2 :
                    return "create_ticket"
                case 3 :
                    return "create_ticket"
                case 4 :
                    return "rag_rewrite_query"
                case 5 :
                    return "konsultasi"
        else :
            END


    builder.add_conditional_edges("human_node", followup_human_node)

    builder.add_edge("konsultasi", END)
    builder.add_edge("create_ticket", END)

    builder.add_edge("rag_rewrite_query", "rag_search")
    builder.add_edge("rag_search", "rag_answer")
    builder.add_edge("rag_answer", END)



    graph = builder.compile()

    result = graph.invoke(state)
    print(result["answer"])

