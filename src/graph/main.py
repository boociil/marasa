from langgraph.graph import StateGraph, START, END

from src.graph.state import BPSState
from src.graph.nodes.registrasi import registrasi
from src.graph.nodes.set_layanan import set_layanan
from src.graph.nodes.rag import data_or_analysis_router, rag_rewrite_query, rag_search, rag_answer
from src.graph.nodes.complaint import create_ticket
from src.graph.nodes.end_checker import end_checker
from src.graph.nodes.human_node import human_node
from src.graph.nodes.konsultasi import konsultasi

from src.graph.db.models import User, ChatSession, ChatMessage, Ticket, get_user_by_phone, get_or_create_active_session, load_last_messages



def main_chat(phoneNumber: str, name: str, text: list[str], isfromMe: bool): 

    state = {
        "session_id": None,
        "session_done": False,
        "layanan_type": 0,
        "need_human": False,
        "is_done": False,
    
        "nama": name,
        "notelp": phoneNumber,
        
        "answer": [],
        "new_chat": text,
        "chat_history": [],

        "use_ai": False,
        "is_system": False,

        "rag_table_id": [],
        "rag_judul": [],
    }

    builder = StateGraph(BPSState)
    # nodes
    
    builder.add_node("registrasi", registrasi)
    builder.add_node("set_layanan", set_layanan)
    builder.add_node("end_checker", end_checker)
    builder.add_node("human_node", human_node)
    builder.add_node("konsultasi", konsultasi)
    builder.add_node("create_ticket", create_ticket)
    builder.add_node("data_or_analysis_router", data_or_analysis_router)
    builder.add_node("rag_rewrite_query", rag_rewrite_query)
    builder.add_node("rag_search", rag_search)
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
                    return "create_ticket"
                case 4 :
                    return "data_or_analysis_router"
                case 5 :
                    return "konsultasi"
        else :
            END


    builder.add_conditional_edges("human_node", followup_human_node)

    builder.add_edge("konsultasi", END)
    builder.add_edge("create_ticket", END)

    builder.add_edge("data_or_analysis_router", "rag_rewrite_query")
    builder.add_edge("rag_rewrite_query", "rag_search")
    builder.add_edge("rag_search", "rag_answer")
    builder.add_edge("rag_answer", END)
    graph = builder.compile()
    result = graph.invoke(state)

    print(result)

    try:
        session = ChatSession.get_by_id(result['session_id'])
        if not result['is_system'] :
            for item_text in result["new_chat"] :
                ChatMessage.create(
                    session = session,
                    role = "user",
                    content = item_text,
                )
            for item_text in result["answer"] :
                ChatMessage.create(
                    session = session,
                    role = "bot",
                    content = item_text,
                )
        session.use_ai = result['use_ai']
        session.is_done = result['session_done']
        session.need_human = result['need_human']
        if result['need_human'] == True :
            session.is_done = True
        session.save()
    except ChatSession.DoesNotExist:
        print()
    
    return result["answer"]

