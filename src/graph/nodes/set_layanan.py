from src.graph.db.models import get_or_create_active_session
from src.graph.text import menu_bps

def set_layanan(state):
    session, baru_status = get_or_create_active_session(state['notelp'])
    if baru_status :
        state["answer"] = [menu_bps]
        state['is_done'] = True
    elif session.layanan == 0 : 
        number = 0
        for item in state['new_chat']:
            if item in ['1','2','3','4','5'] :
                number = int(item)
        session.layanan = number
        session.save()

    if session.layanan == 0 :
        state["answer"] = []
        state['is_done'] = True
    
    return state