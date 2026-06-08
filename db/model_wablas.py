from datetime import datetime
from typing import Optional, List, Literal, Dict
from pydantic import BaseModel, HttpUrl

class GroupDetail(BaseModel):
    sender: Optional[str]= ""
    subject: Optional[str]= ""
    owner: Optional[str]= ""
    desc: Optional[str]= ""
    participants: Optional[List[str]] = ""

class WablasIncomingMessage(BaseModel):
    id: str
    pushName: str
    isGroup: bool
    group: GroupDetail
    
    # Keterangan gambar (caption) jika ada, jika tidak ada biasanya string kosong
    message: str 
    phone: str
    
    # Membatasi tipe pesan agar kita tahu cara menanganinya (text, image, video, document, dll)
    messageType: str 
    
    # Data spesifik untuk media (Image/Video/Dokumen)
    file: Optional[str]
    url: Optional[str] = None # Akan tervalidasi sebagai URL jika tidak kosong
    mimeType: Optional[str]
    
    deviceId: Optional[str]
    sender: str
    isFromMe: bool
    timestamp: datetime
    
    # Gunakan Optional[HttpUrl] atau str karena profileImage bisa kosong jika user tidak punya foto
    profileImage: Optional[str] = None


