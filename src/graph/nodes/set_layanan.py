from src.graph.db.models import get_or_create_active_session, load_last_messages
from src.graph.text import menu_bps

def set_layanan(state):
    session, baru_status = get_or_create_active_session(state['notelp'])
    state["session_id"] = session.get_id()
    state["layanan_type"] = session.layanan
    state["chat_history"] = load_last_messages(session)

    if state["layanan_type"] == 0:
        number = 0
        for item in state['new_chat']:
            if item in ['1','2','3','4','5'] :
                number = int(item)
        session.layanan = number
        session.save()

        if number != 0 :
            state['layanan_type'] = number
            state["answer"] = ["Apa yang bisa kami bantu hari ini?"]
            state['is_done'] = True
            state["is_system"] = True  
        else :
            state["answer"] = [menu_bps]
            state['is_done'] = True
            state["is_system"] = True
    
        
        if state['layanan_type'] == 4 :
            state['use_ai'] = True
    return state