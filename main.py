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
load_dotenv()



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
        # if len(session_to_work) > 0 :
        #     logger.info(session_to_work)
        for item in session_to_work : 
            session_id = item.id
            if session_id in session_in_works:
                continue
            session_in_works.add(session_id)

            all_messages = list(await ChatMessage.select().where(ChatMessage.session == item).order_by(ChatMessage.created_at).aio_execute())
            logger.info(all_messages)
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
async def wablas(data: WablasIncomingMessage):
    global id_pesan
    if data.phone != '6282195195502':
        return {"status": True}
    logger.info(data)

    if data.message.strip() == '' :
        return {"status": True}
    if data.id in id_pesan :
        return {"status": True}
    
    if len(id_pesan) >= 100 :
        id_pesan = id_pesan[:50]

    id_pesan.append(data.id)
    phone = data.phone
    user = await get_user_by_phone(phone)

    session, stop, send_start_layanan = await set_layanan(user, data)
    if stop :
        return {"status": True}
    
    user, stop, send_start_layanan = await registrasi(user, session, data)    
    if send_start_layanan :
        await start_layanan(user, session)
    if stop :
        return {"status": True}

    await ChatMessage.aio_create(
        session = session,
        role = "user",
        content = data.message,
    )

    return {"status": True}


@app.get("/text")
async def text():
    return {"status": True}