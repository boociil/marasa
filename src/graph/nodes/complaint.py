import uuid

def create_ticket(state):
    ticket_id = str(uuid.uuid4())[:8]
    state["ticket_id"] = ticket_id
    state["answer"] = f"Pengaduan Anda tercatat dengan tiket #{ticket_id}"
    return state