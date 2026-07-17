from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class GroupDetail(BaseModel):
    sender: Optional[str] = ""
    subject: Optional[str] = ""
    owner: Optional[str] = ""
    desc: Optional[str] = ""
    participants: Optional[List[str]] = Field(default_factory=list)

class WablasIncomingMessage(BaseModel):
    id: str
    pushName: str = "" 
    isGroup: bool = False
    
    group: Optional[GroupDetail] = None 
    
    message: str = "" 
    phone: str
    
    messageType: str = "text"
    

    file: Optional[str] = None
    url: Optional[str] = None 
    mimeType: Optional[str] = None
    
    deviceId: Optional[str] = None
    sender: str = ""
    isFromMe: bool = False
    timestamp: datetime
    
    profileImage: Optional[str] = None