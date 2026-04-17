from typing import TypedDict, List, Optional

class BPSState(TypedDict):
    session_id: str
    session_done: bool
    layanan_type: int # 1: konsultasi 2. Pengaduan Terkait Layanan, 3. Pengaduan lainnya, 4. Panduan, 5. Lainnya
    need_human: bool
    is_done: bool
    
    nama: str
    notelp: str
    nama_lengkap: str
    
    # rag
    rag_query: Optional[str]
    rag_context: list[str]
    rag_source: list[str]
    
    # outputs
    answer: list[str]
    new_chat: List[str]
    chat_history: List[str]
