from db.models import User, Ticket
from typing import List

async def create_ticket(user: User, message: List[str]):
    new_chat = "\n".join(message)
    await Ticket.aio_create(
        user = user, 
        content = new_chat
    )