from fastapi import FastAPI
from pydantic import BaseModel
# from src.query_data import query_rag
from src.graph.main import main_chat
from contextlib import asynccontextmanager
import asyncio
import requests
from dotenv import load_dotenv
import os
from peewee import fn
from src.graph.db.models import User, ChatSession, ChatMessage, get_user_by_phone
from datetime import datetime, timedelta
from fastapi_utils.tasks import repeat_every

load_dotenv()

app = FastAPI()

@app.on_event("startup")
@repeat_every(seconds=60)
def iddle_task():
    print("asasasasasas")
    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
    idle_sessions = (
        ChatSession
        .select(
            ChatSession,
            fn.MAX(ChatMessage.created_at).alias("last_chat_time")
        )
        .where(
            (ChatSession.layanan == 3) &
            (ChatSession.is_done == False)
        )
        .join(ChatMessage)
        .group_by(ChatSession)
        .having(fn.MAX(ChatMessage.created_at) < ten_minutes_ago)
    )

    for item in idle_sessions :
        user = get_user_by_phone(item.phone)
        item.is_done = True
        item.save()
        requests.post(os.getenv('URL_JS')+"/send-message", json={'jid': user.jid, 'text': 'Terima kasih sudah menghubungi *Marasa by BPS Sulbar*. Jangan ragu hubungi kami lagi jika butuh bantuan lainnya. 😊'})


class Param(BaseModel):
   jid: str
   phoneNumber: str
   name: str
   text: list[str]
   isfromMe: bool

@app.post("/")
def read_root(param: Param):
    print("main")
    print(param)
    # print(param.phoneNumber)
    # if param.phoneNumber in ['6281342774989', '6281399152242', '6282344852209', '6285255178499', '6285342419813', '6281218189650']:
    if param.isfromMe :
        jid, answer =  main_chat(param.jid, param.phoneNumber, param.name, param.text, param.isfromMe)
        path_ori = []
        for item_answer in answer:
            if item_answer.file_path is None :
                requests.post(os.getenv('URL_JS')+"/send-message", json={'jid': jid, 'text': item_answer.text})
            else :
                if item_answer.file_path not in path_ori :
                    with open(item_answer.file_path, 'rb') as f:
                        # FORMAT: (filename, file_object, mimetype)
                        files = {
                            'image': ('image.jpg', f, 'image/jpeg') 
                        }
                        
                        requests.post(os.getenv('URL_JS')+"/send-message", data={'jid': jid, 'text': item_answer.text}, files=files)
                    path_ori.append(item_answer.file_path)
                
    else :
        return []
    # return main_chat(phoneNumber, name, text, isfromMe)

@app.post("/health_check")
def health_check():
    print("health_check")
    return["a", "b"]