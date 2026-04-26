from typing import TypedDict, List, Optional
from pydantic import BaseModel
from typing import Optional

class RagPublikasiBRS(BaseModel):
    id: str
    type: str
    bps_id: str
    title: str 
    halaman: int
    content: str
    rl_date: str
    score: float
    def print(self):
        return f"""ID Pengetahuan :  {self.id}
Judul : {self.title}
content : {self.content}
Release : {self.rl_date}
"""

class RagData(BaseModel):
    id: str
    judul: str 
    url: str
    content: str
    score: float
    def print(self):
        return f"""ID Pengetahuan :  {self.id}
Judul : {self.judul}
content : {self.content}
Url : {self.url}
"""

class AnswerModel(BaseModel):
    type: str #file, text, system
    file_path: Optional[str] = None
    text: Optional[str] = None

class QuestionModel(BaseModel):
    ques: Optional[str] = None
    rag_ques: list[str] = []
    answer: list[AnswerModel] = []
    rag_publikasi_brs: list[RagPublikasiBRS] = []
    rag_data: list[RagData] = []
    rag_publikasi_brs_output: list[RagPublikasiBRS] = []
    rag_data_output: list[RagData] = []

class ChatMessage(BaseModel):
    role: str
    content: str

class BPSState(TypedDict):
    session_id: Optional[str]
    session_done: bool
    layanan_type: int # 1: konsultasi 2. Pengaduan Terkait Layanan, 3. Pengaduan lainnya, 4. Panduan, 5. Lainnya
    need_human: bool
    is_done: bool
    
    jid: str
    nama: str
    notelp: str
    
    # rag
    use_ai: bool
    question: List[QuestionModel]
    sis_answer: List[str]
   
    # outputs
    new_chat: List[str]
    chat_history: List[ChatMessage]
