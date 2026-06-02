from typing import TypedDict, List, Optional
from typing import Optional

from db.model_rag import QuestionModel, ChatMessage

class BPSState(TypedDict):
    need_human: bool
    is_done: bool
    
    nama: str
    notelp: str
    nama_lengkap: str
    user_is_db: bool
    
    # rag
    use_ai: bool
    question: List[QuestionModel]
   
    # outputs
    new_chat: List[str]
    chat_history: List[ChatMessage]
