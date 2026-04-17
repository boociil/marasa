from typing import TypedDict, List, Optional

class BPSState(TypedDict):

    nama: str
    notelp: str
    nama_lengkap: Optional[str]
    
    # workflow state
    is_registered: bool
    intent: Optional[str]
    service_type: Optional[str]
    
    # rag
    rag_context: Optional[str]
    
    # outputs
    answer: Optional[str]
    ticket_id: Optional[str]
    
    # conversation control
    is_followup: Optional[bool]
    is_done: Optional[bool]
    
    chat_history: List[str]