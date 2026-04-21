import uuid

def create_ticket(state):
    ticket_id = str(uuid.uuid4())[:8]
    state["answer"] = f"Pengaduan Anda tercatat dengan ##"
    return state