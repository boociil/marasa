from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
# from src.query_data import query_rag
from src.graph.main import main_chat, build_graph
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

# cache registras => registrasi_notlp
# cache source => minta link (pdf)
# 


class MemoryStore:
    def __init__(self):
        self.data = {}
    def cache_put(self, key, value):
        self.data[key] = value
    def cache_get(self, key):
        return self.data.get(key)
    def cache_delete(self, key):
        del self.data.pop(key)

memory_store = MemoryStore()

graph = build_graph()
app = FastAPI()

@app.on_event("startup")
@repeat_every(seconds=60)
def iddle_task():
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
async def read_root(param: Param, bg: BackgroundTasks):
    print("main")
    print(param)
    # print(param.phoneNumber)
#     if param.phoneNumber in ['6285283036590'
# ,'6285234609332'
# ,'6281218632475'
# ,'6282122756354'
# ,'6285241027007'
# ,'6287731414134'
# ,'6282195195502'
# ,'6285299736234'
# ,'6282191347744'
# ,'6281212173630'
# ,'6285255136252'
# ,'6281244261166'
# ,'6281311952627'
# ,'6285242427076'
# ,'6281342560233'
# ,'6281342547923'
# ,'6281256161600'
# ,'6285338878227'
# ,'6281341993737'
# ,'6285242010447'
# ,'6281343521023'
# ,'6281342902240'
# ,'6282210289671'
# ,'6285340778508'
# ,'6282259656015'
# ,'6289618834285'
# ,'6281384233473'
# ,'628114002481'
# ,'6281328253790'
# ,'6282235078215'
# ,'6285792017002'
# ,'6285342419813'
# ,'6282349063633'
# ,'6285340886610'
# ,'6285238809301'
# ,'6282344852210'
# ,'6285255178499'
# ,'6282344852209'
# ,'6281315546806'
# ,'6282292278519'
# ,'6281328747856'
# ,'6281319069547'
# ,'6281342774989'
# ,'6282310324774'
# ,'6282227397717'
# ,'6285277397129'
# ,'6285299230996'
# ,'628114221767'
# ,'6281241666770'
# ,'6281354786929'
# ,'628982250711'
# ,'6285395839898'
# ,'6281241840124'
# ,'6282292779039'
# ,'6282311259355'
# ,'6281258345220'
# ,'6282343990313'
# ,'6281399152242'
# ,'6282214072032'
# ,'6281218189650'
# ,'6285726287612'
# ,'6282394517916'
# ,'6285157128522'
# ,'6282196956817'
# ,'6281227577682'
# ,'6283115313346'
# ,'6285280165627'
# ,'6282297042070'
# ,'6289650807314'
# ,'6282191167862'
# ,'6282210467478'
# ,'6282319192651'
# ,'6288224735330']:
    if param.isfromMe :
        asyncio.create_task(main_chat( graph, param.jid, param.phoneNumber, param.name, param.text, memory_store, param.isfromMe))
        print('asasasasa')
        return []
    else :
        return []
    # return main_chat(phoneNumber, name, text, isfromMe)

@app.post("/health_check")
def health_check():
    print("health_check")
    return["a", "b"]