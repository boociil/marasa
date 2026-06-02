from langgraph.graph import StateGraph, START, END

from graph.state import BPSState
from graph.nodes.rag import pecah_question_and_transform_untuk_rag, rag_search, rag_validate, rag_answer
from graph.nodes.end_checker import end_checker
from graph.nodes.human_node import human_node
from graph.state import AnswerModel
import requests
import os
import time
from dotenv import load_dotenv, find_dotenv
from typing import List, Dict
from db.models import get_user_by_phone

# 1. LOAD ENV (Parent Folder)
load_dotenv(find_dotenv())

from db.models import ChatSession, ChatMessage

ai_disclaimen = "*AI dapat membuat kesalahan"

def build_graph(): 
    builder = StateGraph(BPSState)
    # nodes
    
    builder.add_node("end_checker", end_checker)
    builder.add_node("human_node", human_node)

    builder.add_node("pecah_question_and_transform_untuk_rag", pecah_question_and_transform_untuk_rag)
    builder.add_node("rag_search", rag_search)
    builder.add_node("rag_validate", rag_validate)
    builder.add_node("rag_answer", rag_answer)
    

    builder.add_edge(START, "end_checker")

    def followup_end_checker(state):
        return "human_node" if not state["is_done"] else END

    builder.add_conditional_edges("end_checker", followup_end_checker)

    def followup_human_node(state):
        if not state["need_human"] :
            return "pecah_question_and_transform_untuk_rag"
        else :
            return END


    builder.add_conditional_edges("human_node", followup_human_node)

    builder.add_edge("pecah_question_and_transform_untuk_rag", "rag_search")
    builder.add_edge("rag_search", "rag_validate")
    builder.add_edge("rag_validate", "rag_answer")
    builder.add_edge("rag_answer", END)

    return builder.compile()
   

async def main_chat(graph, session: ChatSession, message: List[str]): 
    user = get_user_by_phone(session.phone)

    state = {
        "need_human": False,
        "is_done": False,

        "nama": user.nama,
        "nama_lengkap": user.nama_lengkap,
        "notelp": session.phone,

        "use_ai": False,
        "question": [],

        "new_chat": message,
        "chat_history": [],
    }

    
    result = await graph.ainvoke(state)
    
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
