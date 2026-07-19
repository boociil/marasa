from typing import TypedDict, List

from db.model_rag import QuestionModel, ChatMessage

class BPSState(TypedDict):
    type: str = 'WA'
    check: str
    
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
