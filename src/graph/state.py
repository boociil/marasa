from typing import TypedDict, List, Optional

class BPSState(TypedDict):
    session_id: Optional[str]
    session_done: bool
    layanan_type: int # 1: konsultasi 2. Pengaduan Terkait Layanan, 3. Pengaduan lainnya, 4. Panduan, 5. Lainnya
    need_human: bool
    is_done: bool
    
    nama: str
    notelp: str
    nama_lengkap: Optional[str]
    
    # rag
    use_ai: bool
    rag_type: Optional[str]
    rag_query: Optional[str]
    rag_context_pdf: list[str]

    rag_table_url: list[str]
    rag_table_judul: list[str]
    # rag_source: list[str]
    
    # outputs
    answer: list[str]
    new_chat: List[str]
    chat_history: List[str]
    is_system: bool
