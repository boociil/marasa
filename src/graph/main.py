from langgraph.graph import StateGraph, END

from state import BPSState
from nodes.auth import check_registration
from nodes.router import route_intent
from nodes.rag import rag_search, generate_stat_answer
from nodes.complaint import create_ticket
from nodes.general import general_ai
from nodes.followup import detect_followup
from nodes.end_checker import end_checker

def main_chat(phoneNumber: str, name: str, text: list[str], isfromMe: bool): 
    state = {
        "user_id": "user_1",
        "message": "Ada data kemiskinan 2023?",
        "chat_history": []
    }


    builder = StateGraph(BPSState)

    # nodes
    builder.add_node("check_registration", check_registration)
    builder.add_node("router", route_intent)
    builder.add_node("rag_search", rag_search)
    builder.add_node("rag_answer", generate_stat_answer)
    builder.add_node("create_ticket", create_ticket)
    builder.add_node("general_ai", general_ai)
    builder.add_node("followup", detect_followup)
    builder.add_node("end_checker", end_checker)

    # entry
    builder.set_entry_point("check_registration")

    # registration routing
    def registered_router(state):
        return "router" if state["is_registered"] else END

    builder.add_conditional_edges(
        "check_registration",
        registered_router
    )

    # service routing
    def service_router(state):
        return state["service_type"]

    builder.add_conditional_edges(
        "router",
        service_router,
        {
            "konsultasi_statistik": "rag_search",
            "pengaduan_layanan": "create_ticket",
            "pengaduan_lainnya": "create_ticket",
            "lainnya": "general_ai",
        }
    )

    builder.add_edge("rag_search", "rag_answer")
    builder.add_edge("rag_answer", "followup")
    builder.add_edge("create_ticket", "followup")
    builder.add_edge("general_ai", "followup")

    # followup routing
    def followup_router(state):
        return "router" if not state["is_followup"] else "end_checker"

    builder.add_conditional_edges("followup", followup_router)

    # end checker
    def end_router(state):
        return END if state["is_done"] else END  # wait next message externally

    builder.add_conditional_edges("end_checker", end_router)

    graph = builder.compile()

    result = graph.invoke(state)
    print(result["answer"])


    return []
