from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from graph.main import main_chat, build_graph
import asyncio
from dotenv import load_dotenv
import os
from loguru import logger
from db.models import iddle_task
from cache import shared_cache

load_dotenv()


if not os.path.exists("log"):
    os.makedirs("log")

logger.add(
    "log/api_{time:YYYY-MM-DD}.log", # Nama file akan jadi seperti log/api_2026-05-26.log
    rotation="00:00",                # Buat file baru setiap jam 12 malam (tengah malam)
    retention="30 days",             # Opsional: Otomatis hapus file log yang lebih tua dari 30 hari
    level="INFO"
)



graph = build_graph()
app = FastAPI()

@app.on_event("startup")
@repeat_every(seconds=60)
def iddle_task():
    asyncio.create_task(iddle_task())


class Param(BaseModel):
   jid: str
   phoneNumber: str
   name: str
   text: list[str]
   isfromMe: bool

@app.post("/")
async def read_root(param: Param, bg: BackgroundTasks):
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
        asyncio.create_task(main_chat( graph, param.jid, param.phoneNumber, param.name, param.text, param.isfromMe))
        return []
    else :
        return []
    # return main_chat(phoneNumber, name, text, isfromMe)

@app.post("/health_check")
def health_check():
    return["a", "b"]