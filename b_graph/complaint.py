
from db.model_wablas import WablasIncomingMessage
from db.models import WablasIncomingMessage, User, Ticket
from typing import List

def create_ticket(user: User, message: List[str]):
    new_chat = "\n".join(message)
    Ticket.create(
        user = user, 
        content = new_chat
    )