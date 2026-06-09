from langgraph.graph import StateGraph, START, END

from graph.state import BPSState
from graph.nodes.rag import pecah_question_and_transform_untuk_rag, rag_search, rag_rerank, rag_answer
from graph.nodes.checker import checker
from db.model_rag import AnswerModel
from dotenv import load_dotenv, find_dotenv
from typing import List, Dict
from db.models import get_user_by_phone
from wablas.send import send_simple_text, send_simple_image
from _global import logger

# 1. LOAD ENV (Parent Folder)
load_dotenv(find_dotenv())

from db.models import ChatSession, ChatMessage

ai_disclaimen = "*AI dapat membuat kesalahan"

def build_graph(): 
    builder = StateGraph(BPSState)
    # nodes
    
    builder.add_node("checker", checker)
    builder.add_node("pecah_question_and_transform_untuk_rag", pecah_question_and_transform_untuk_rag)
    builder.add_node("rag_search", rag_search)
    builder.add_node("rag_rerank", rag_rerank)
    builder.add_node("rag_answer", rag_answer)
    

    builder.add_edge(START, "checker")

    def followup_checker(state):
        return "pecah_question_and_transform_untuk_rag" if state["check"] == 'TANYA' else END

    builder.add_conditional_edges("checker", followup_checker)

    builder.add_edge("pecah_question_and_transform_untuk_rag", "rag_search")
    builder.add_edge("rag_search", "rag_rerank")
    builder.add_edge("rag_rerank", "rag_answer")
    builder.add_edge("rag_answer", END)

    return builder.compile()
   

async def main_chat(graph, session: ChatSession, message: List[str]): 
    user = await get_user_by_phone(session.phone)

    state = {
        "check": 'TANYA',

        "nama": user.nama,
        "nama_lengkap": user.nama_lengkap,
        "notelp": session.phone,

        "question": [],

        "new_chat": message,
        "chat_history": [],
    }

    
    result = await graph.ainvoke(state)

    if result['check'] == 'PUAS' :
        await send_simple_text(user.notelp, 'Terima kasih sudah menghubungi *Marasa by BPS Sulbar*. Jangan ragu hubungi kami lagi jika butuh bantuan lainnya. 😊')
        session.is_done = True;
        await session.aio_save()
        return
    elif result['check'] == 'ADMIN' :
        await send_simple_text(user.notelp, 'Siap, kak {user.nama_lengkap}! Saya bantu hubungkan dengan petugas kami ya supaya bisa dibantu lebih detail. Mohon tunggu sebentar ya! ☕🤝')
        session.is_done = True;
        await session.aio_save()
        return
    elif  result['check'] == 'OFF' :
        await send_simple_text(user.notelp, 'Waduh, maaf banget nih, sepertinya pertanyaan tadi di luar topik statistik BPS. Yuk, kita kembali ke jalur utama!')
        session.is_done = True;
        await session.aio_save()
        return
    #TANYA
 
    answer = []
    for item_ques in result['question']:
        for item_answer in item_ques.answer:
            answer.append(item_answer)
            logger.info(item_answer.text)
            logger.info("")

    if len(result['question']) > 0 :
        answer.append(AnswerModel(type="text", text=ai_disclaimen))

    path_ori = []
    for item_answer in answer:
        if item_answer.file_path is None :
            await send_simple_text(user.notelp, item_answer.text)
        else :
            if item_answer.file_path not in path_ori :
                await send_simple_image(user.notelp, item_answer.text, item_answer.file_path)
                path_ori.append(item_answer.file_path)

    for item_ques in result['question']:
        for item_answer in item_ques.answer:
            if item_answer.file_path is None :
                await ChatMessage.aio_create(
                    session = session,
                    role = "bot",
                    content = item_answer.text,
                )
            else :
                await ChatMessage.aio_create(
                    session = session,
                    role = "bot",
                    content =  f"{item_answer.file_path} {item_answer.text}",
                )


async def main_chat_cmd(graph, text: list[str], chat_history: list[str]): 
    logger.info(text)
    logger.info(chat_history)
    state = {
        "check": 'TANYA',

        "nama": '',
        "nama_lengkap": '',
        "notelp": '',

        "question": [],

        "new_chat": text,
        "chat_history": chat_history,
    }

    result = await graph.ainvoke(state)
    answer = []
    for item_ques in result['question']:
        for item_answer in item_ques.answer:
            answer.append(item_answer)
    
    return answer
