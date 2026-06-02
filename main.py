from fastapi import FastAPI
from contextlib import asynccontextmanager
from graph.main import build_graph, main_chat
from dotenv import load_dotenv
import asyncio
from loguru import logger
from db.models import iddle_task_ai, iddle_task_konsultasi, ChatMessage, get_active_session
from db.model_wablas import WablasIncomingMessage
import os
from db.models import get_user_by_phone
from b_graph.set_layanan import set_layanan
from b_graph.registrasi import registrasi
from db.model_wablas import WablasIncomingMessage
from db.models import WablasIncomingMessage

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

session_in_works = []

async def debounce_per_user_worker():    
    while True:
        await asyncio.sleep(0.5) # Loop cek setiap 1 detik
        session_to_work = get_active_session(session_in_works)
        
        for item in session_to_work : 
            all_messages = (
                ChatMessage
                    .select()
                    .where(ChatMessage.session == item.id)
                    .order_by(ChatMessage.created_at)
            )
            new_message = []
            for item_m in all_messages :
                if item_m.role == "user" :
                    new_message.append(item_m.content)
                elif item_m.role == "bot" :
                    new_message = []
            asyncio.create_task(main_chat( graph, item, new_message))

async def process_per_minute():    
    while True:
        await asyncio.sleep(60) # per menit
        asyncio.create_task(iddle_task_ai())
        asyncio.create_task(iddle_task_konsultasi())

# 3. Lifespan Manager (Mengatur startup & shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(debounce_per_user_worker())
    worker_iddle = asyncio.create_task(process_per_minute())
    yield
    worker_task.cancel()
    worker_iddle.cancel


app = FastAPI(lifespan=lifespan)




@app.post("/")
async def wablas(message: WablasIncomingMessage):
    phone = message.phone
    user = get_user_by_phone(phone)

    session, baru_status, stop = set_layanan(session, baru_status, user, message)
    if stop :
        return {"status": True}
    stop = registrasi(user, message)

    ChatMessage.create(
        session = session,
        role = "user",
        content = message.message,
    )
    

    return {"status": True}