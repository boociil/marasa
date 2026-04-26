from src.graph.db.models import User, get_user_by_phone
from src.graph.db.models import Ticket

def create_ticket(state):
    user = get_user_by_phone(state['notelp'])
    new_chat = "\n".join(state["new_chat"])
    Ticket.create(
        user = user, 
        content = new_chat
    )
    state["sis_answer"] = [f"Terimakasih Sudah menghubungi *Marasa by BPS Sulbar*, Pengaduan anda akan kami proses secepatnya"]
    state['session_done'] = True
    return state