from typing import TypedDict, List, Optional
from typing import Optional

from db.models_other import QuestionModel, ChatMessage

class BPSState(TypedDict):
    session_id: Optional[str]
    session_done: bool
    layanan_type: int # 1: konsultasi 2. Pengaduan Terkait Layanan, 3. Pengaduan lainnya, 4. Panduan, 5. Lainnya
    need_human: bool
    is_done: bool
    
    nama: str
    notelp: str
    nama_lengkap: str
    user_is_db: bool
    
    # rag
    use_ai: bool
    question: List[QuestionModel]
    sis_answer: List[str]
   
    # outputs
    new_chat: List[str]
    chat_history: List[ChatMessage]
