from fastapi import FastAPI
from contextlib import asynccontextmanager
from graph.main import build_graph, main_chat
from dotenv import load_dotenv
import asyncio
from _global import logger
from db.models import iddle_task_ai, iddle_task_konsultasi, ChatMessage, close_24_hour, get_active_session_not_arr
from db.model_wablas import WablasIncomingMessage
from db.models import get_user_by_phone
from b_graph.set_layanan import set_layanan
from b_graph.registrasi import registrasi
from b_graph.start_layanan import start_layanan
import time

load_dotenv()
graph = build_graph()

# Ubah menjadi 'set' agar pencarian dan penghapusan O(1) dan lebih aman dari duplikasi
session_in_works_id = set()

def on_finish_callback(task, id_session: str):
    try:
        task.result()
    except Exception:
        logger.exception(f"main_chat error on session {id_session}")
    finally:
        session_in_works_id.discard(id_session)

async def debounce_per_user_worker():    
    while True:
        await asyncio.sleep(1) # Loop cek setiap 1 detik
        if len(session_in_works_id) >= 4 :
            continue
            
        session_to_work = await get_active_session_not_arr(list(session_in_works_id))
        for item in session_to_work : 
            session_id = item.id
            if session_id in session_in_works_id:
                continue
            session_in_works_id.add(session_id)

            all_messages = list(await ChatMessage.select().where(ChatMessage.session == item).order_by(ChatMessage.created_at).aio_execute())
            all_messages.reverse()
            older_message = []
            new_message = []

            for item_m in all_messages :
                if item_m.role == "user":
                    new_message.append(item_m.content)
                elif item_m.role == "bot":
                    for msg in new_message:
                        older_message.append(f"user : {msg}")
                    older_message.append(f"bot : {item_m.content}")
                    new_message.clear()

            task = asyncio.create_task(main_chat(graph, item, new_message, older_message))
            task.add_done_callback(
                lambda t, s_id=session_id: on_finish_callback(t, s_id)
            )


async def process_per_minute():    
    while True:
        await asyncio.sleep(60) # per menit
        asyncio.create_task(iddle_task_ai(list(session_in_works_id)))
        asyncio.create_task(iddle_task_konsultasi())


db_buffer = {}

async def process_per_1_second():    
    while True:
        await asyncio.sleep(1) 
        current_time = time.time()
        
        # Iterasi menggunakan list(keys()) agar aman jika dictionary dimodifikasi saat proses
        for phone in list(db_buffer.keys()):
            buffer_info = db_buffer.get(phone)
            if not buffer_info:
                continue
                
            # Debounce: Proses jika sudah tidak ada pesan baru dari user ini selama 2 detik
            if current_time - buffer_info['lastupdate'] >= 2.0:
                chats = buffer_info['chat']
                
                # Segera hapus dari buffer agar pesan baru berikutnya memulai sesi baru
                del db_buffer[phone]
                user = await get_user_by_phone(phone)
                
                for data in chats:
                    try:
                        session, stop, send_start_layanan = await set_layanan(user, data)
                        if stop:
                            continue # Gunakan continue, JANGAN return
                        
                        user, stop_, send_start_layanan_ = await registrasi(user, session, data)
                        if stop_:
                            continue

                        if send_start_layanan or (stop_ and send_start_layanan_):
                            await start_layanan(user, session)
                            continue

                        await ChatMessage.aio_create(
                            session = session,
                            role = "user",
                            content = data.message,
                        )
                    except Exception as e:
                        logger.exception(f"Error saat memproses antrean chat untuk {phone}: {str(e)}")


# 3. Lifespan Manager (Mengatur startup & shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await close_24_hour()
    
    worker_chat = asyncio.create_task(process_per_1_second())
    worker_task = asyncio.create_task(debounce_per_user_worker())
    worker_iddle = asyncio.create_task(process_per_minute())
    yield
    worker_chat.cancel()
    worker_task.cancel()
    worker_iddle.cancel()


app = FastAPI(lifespan=lifespan)

id_pesan = []

@app.post("/")
async def wablas(data: WablasIncomingMessage):
    global id_pesan
    if data.isGroup:
        return {"status": True}
    if not checkHpGroup(data.phone):
        return {"status": True}
    if not data.message or data.message.strip() == '':
        return {"status": True}
    if data.id in id_pesan:
        return {"status": True}
    
    logger.info(f"Incoming message from {data.phone}: {data.message}")
    
    if len(id_pesan) >= 100:
        id_pesan = id_pesan[-50:] 

    id_pesan.append(data.id)
    phone = data.phone
    
    if phone not in db_buffer:
        db_buffer[phone] = {
            "no_hp": phone,
            "chat": [], 
            "lastupdate": time.time(),
        }

    db_buffer[phone]['chat'].append(data)
    db_buffer[phone]['lastupdate'] = time.time()

    return {"status": True}


@app.get("/text")
async def text():
    return {"status": True}

def checkHpGroup(phone):
    # Logika disederhanakan
    return phone in ['6282195195502']