from langgraph.graph import StateGraph, START, END

from src.graph.state import BPSState
from src.graph.nodes.registrasi import registrasi
from src.graph.nodes.set_layanan import set_layanan
from src.graph.nodes.rag import pecah_question_and_transform_untuk_rag, rag_search, rag_validate, rag_answer
from src.graph.nodes.complaint import create_ticket
from src.graph.nodes.end_checker import end_checker
from src.graph.nodes.human_node import human_node
from src.graph.nodes.konsultasi import konsultasi
from src.graph.state import AnswerModel
import requests
import os
import time
from dotenv import load_dotenv, find_dotenv

# 1. LOAD ENV (Parent Folder)
load_dotenv(find_dotenv())

from src.graph.db.models import ChatSession, ChatMessage

ai_disclaimen = "*AI dapat membuat kesalahan"

def build_graph(): 
    builder = StateGraph(BPSState)
    # nodes
    
    builder.add_node("registrasi", registrasi)
    builder.add_node("set_layanan", set_layanan)
    builder.add_node("end_checker", end_checker)
    builder.add_node("human_node", human_node)
    builder.add_node("konsultasi", konsultasi)
    builder.add_node("create_ticket", create_ticket)

    builder.add_node("pecah_question_and_transform_untuk_rag", pecah_question_and_transform_untuk_rag)
    builder.add_node("rag_search", rag_search)
    builder.add_node("rag_validate", rag_validate)
    builder.add_node("rag_answer", rag_answer)
    

    builder.add_edge(START, "registrasi")

    def followup_registrasi(state):
        return "set_layanan" if not state["is_done"] else END

    builder.add_conditional_edges("registrasi", followup_registrasi)

    def followup_set_layanan(state):
        return "end_checker" if not state["is_done"] else END

    builder.add_conditional_edges("set_layanan", followup_set_layanan)


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
                    return "pecah_question_and_transform_untuk_rag"
                case 4 :
                    return "konsultasi"
                case _:  # Default case
                    return END
        else :
            return END


    builder.add_conditional_edges("human_node", followup_human_node)

    builder.add_edge("konsultasi", END)
    builder.add_edge("create_ticket", END)

    builder.add_edge("pecah_question_and_transform_untuk_rag", "rag_search")
    builder.add_edge("rag_search", "rag_validate")
    builder.add_edge("rag_validate", "rag_answer")
    builder.add_edge("rag_answer", END)

    return builder.compile()
   

async def main_chat(graph, jid: str, phoneNumber: str, name: str, text: list[str], isfromMe: bool): 
    state = {
        "session_id": None,
        "session_done": False,
        "layanan_type": 0,
        "need_human": False,
        "is_done": False,

        "jid": jid,
        "nama": name,
        "nama_lengkap": name,
        "notelp": phoneNumber,
        "user_is_db": False,

        "use_ai": False,
        "question": [],
        "sis_answer": [],

        "new_chat": text,
        "chat_history": [],
    }

    
    result = await graph.ainvoke(state)
    # print(result)
    
    try:
        session = ChatSession.get_by_id(result['session_id'])
        if session.is_done and result['user_is_db']: 
            return []

        for item_text in result["new_chat"] :
            ChatMessage.create(
                session = session,
                role = "user",
                content = item_text,
            )
        for item_text in result["sis_answer"] :
            ChatMessage.create(
                session = session,
                role = "sis",
                content = item_text,
            )
        for item_ques in result['question']:
            for item_answer in item_ques.answer:
                if item_answer.file_path is None :
                    ChatMessage.create(
                        session = session,
                        role = "sis",
                        content = item_answer.text,
                    )
                else :
                    ChatMessage.create(
                        session = session,
                        role = "sis",
                        content = item_answer.file_path,
                    )
        session.use_ai = result['use_ai']
        session.is_done = result['session_done']
        session.need_human = result['need_human']
        if result['need_human'] == True :
            session.is_done = True
        session.save()
    except ChatSession.DoesNotExist:
        print()

    answer = []
    for item_sis in result['sis_answer']:
        answer.append(AnswerModel(type="text", text=item_sis))
    for item_ques in result['question']:
        for item_answer in item_ques.answer:
            answer.append(item_answer)

    if len(result['question']) > 0 :
        answer.append(AnswerModel(type="text", text=ai_disclaimen))

    path_ori = []
    for item_answer in answer:
        if item_answer.file_path is None :
            requests.post(os.getenv('URL_JS')+"/send-message", json={'jid': jid, 'text': item_answer.text})
        else :
            if item_answer.file_path not in path_ori :
                with open(item_answer.file_path, 'rb') as f:
                    # FORMAT: (filename, file_object, mimetype)
                    files = {
                        'image': ('image.jpg', f, 'image/jpeg') 
                    }
                    
                    requests.post(os.getenv('URL_JS')+"/send-message", data={'jid': jid, 'text': item_answer.text}, files=files)
                path_ori.append(item_answer.file_path)
    


async def main_chat_cmd(graph, text: list[str], chat_history: list[str]): 

    state = {
        "session_id": None,
        "session_done": False,
        "layanan_type": 0,
        "need_human": False,
        "is_done": False,

        "jid": "jid",
        "nama": "name",
        "notelp": "notelp",

        "use_ai": False,
        "question": [],

        "new_chat": text,
        "chat_history": [],
    }

    result = await graph.ainvoke(state)

    answer = []
    for item_ques in result['question']:
        for item_answer in item_ques.answer:
            answer.append(item_answer)
    
    return answer
