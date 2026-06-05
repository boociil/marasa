from fastapi import FastAPI
from contextlib import asynccontextmanager
from graph.main import build_graph, main_chat
from dotenv import load_dotenv
import asyncio
from _global import logger
from db.models import iddle_task_ai, iddle_task_konsultasi, ChatMessage, get_active_session, close_24_hour, get_active_session_not_arr
from db.model_wablas import WablasIncomingMessage
import os
from db.models import get_user_by_phone
from b_graph.set_layanan import set_layanan
from b_graph.registrasi import registrasi
from db.db import db

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
session_in_works = set()

def on_finish_callback(task, id_session: str) :
    try:
        task.result()
        if id_session in session_in_works:
            session_in_works.discard(id_session)

    except Exception:
        logger.exception("main_chat error")  

async def debounce_per_user_worker():    
    while True:
        await asyncio.sleep(1) # Loop cek setiap 1 detik
        session_to_work = await get_active_session_not_arr(list(session_in_works))
        
        for item in session_to_work : 
            session_id = item.id
            if session_id in session_in_works:
                continue
            session_in_works.add(session_id)

            all_messages = await db.list(
                ChatMessage
                    .select()
                    .where(ChatMessage.session == session_id)
                    .order_by(ChatMessage.created_at)
            )
            new_message = []
            for item_m in all_messages :
                if item_m.role == "user" :
                    new_message.append(item_m.content)
                elif item_m.role == "bot" :
                    new_message = []

            task = asyncio.create_task(main_chat( graph, item, new_message))
            task.add_done_callback(
                lambda t, session_id=session_id: on_finish_callback(t, session_id)
            )

async def process_per_minute():    
    while True:
        await asyncio.sleep(60) # per menit
        asyncio.create_task(iddle_task_ai())
        asyncio.create_task(iddle_task_konsultasi())

# 3. Lifespan Manager (Mengatur startup & shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await close_24_hour()
    
    worker_task = asyncio.create_task(debounce_per_user_worker())
    worker_iddle = asyncio.create_task(process_per_minute())
    yield
    worker_task.cancel()
    worker_iddle.cancel()


app = FastAPI(lifespan=lifespan)


id_pesan = []

@app.post("/")
async def wablas(message: WablasIncomingMessage):
    if message.id in id_pesan :
        return {"status": True}
    
    if len(id_pesan) >= 100 :
        id_pesan = id_pesan[:50]

    id_pesan.append(message.id)
    phone = message.phone
    user = await get_user_by_phone(phone)

    session, baru_status, stop = await set_layanan(user, message)
    if stop :
        return {"status": True}
    stop = registrasi(user, message)
    if stop :
        return {"status": True}

    await ChatMessage.aio_create(
        session = session,
        role = "user",
        content = message.message,
    )
    

    return {"status": True}