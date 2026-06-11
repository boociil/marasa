from fastapi import FastAPI
from contextlib import asynccontextmanager
from graph.main import build_graph, main_chat
from dotenv import load_dotenv
import asyncio
from _global import logger, session_in_works
from db.models import iddle_task_ai, iddle_task_konsultasi, ChatMessage, close_24_hour, get_active_session_not_arr
from db.model_wablas import WablasIncomingMessage
from db.models import get_user_by_phone
from b_graph.set_layanan import set_layanan
from b_graph.registrasi import registrasi
from b_graph.start_layanan import start_layanan

load_dotenv()
graph = build_graph()

session_in_works.clear()

def on_finish_callback(task, id_session: str) :
    try:
        task.result()
        if session_in_works.get(f'session_in_works__{id_session}', False):
            session_in_works.pop(f'session_in_works__{id_session}')
    except Exception:
        logger.exception("main_chat error")  

async def debounce_per_user_worker():    
    while True:
        await asyncio.sleep(1) # Loop cek setiap 1 detik
        session_to_work = await get_active_session_not_arr()
        # if len(session_to_work) > 0 :
        #     logger.info(session_to_work)
        for item in session_to_work : 
            session_id = item.id
            if session_in_works.get(f'session_in_works__{session_id}', False):
                continue
            session_in_works.set(f'session_in_works__{session_id}', True)

            all_messages = list(await ChatMessage.select().where(ChatMessage.session == item).order_by(ChatMessage.created_at).aio_execute())
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


            task = asyncio.create_task(main_chat( graph, item, new_message, older_message))
            task.add_done_callback(
                lambda t, session_id=session_id: on_finish_callback(t, session_id)
            )
            continue

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
    if data.isGroup :
        return {"status": True}
    if not checkHpGroup(data.phone):
        return {"status": True}
    if data.message.strip() == '' :
        return {"status": True}
    if data.id in id_pesan :
        return {"status": True}
    
    logger.info(data)
    
    if len(id_pesan) >= 100 :
        id_pesan = id_pesan[:50]

    id_pesan.append(data.id)
    phone = data.phone
    user = await get_user_by_phone(phone)

    session, stop, send_start_layanan = await set_layanan(user, data)
    if stop :
        return {"status": True}
    
    user, stop_, send_start_layanan_ = await registrasi(user, session, data)
    if stop_ :
        return {"status": True}

    if send_start_layanan or ( stop_ and send_start_layanan_ ) :
        await start_layanan(user, session)
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

def checkHpGroup(phone):
    if phone in ['6285283036590'
,'6285234609332'
,'6281218632475'
,'6282122756354'
,'6285241027007'
,'6287731414134'
,'6282195195502'
,'6285299736234'
,'6282191347744'
,'6281212173630'
,'6285255136252'
,'6281244261166'
,'6281311952627'
,'6285242427076'
,'6281342560233'
,'6281342547923'
,'6281256161600'
,'6285338878227'
,'6281341993737'
,'6285242010447'
,'6281343521023'
,'6281342902240'
,'6282210289671'
,'6285340778508'
,'6282259656015'
,'6289618834285'
,'6281384233473'
,'628114002481'
,'6281328253790'
,'6282235078215'
,'6285792017002'
,'6285342419813'
,'6282349063633'
,'6285340886610'
,'6285238809301'
,'6282344852210'
,'6285255178499'
,'6282344852209'
,'6281315546806'
,'6282292278519'
,'6281328747856'
,'6281319069547'
,'6281342774989'
,'6282310324774'
,'6282227397717'
,'6285277397129'
,'6285299230996'
,'628114221767'
,'6281241666770'
,'6281354786929'
,'628982250711'
,'6285395839898'
,'6281241840124'
,'6282292779039'
,'6282311259355'
,'6281258345220'
,'6282343990313'
,'6281399152242'
,'6282214072032'
,'6281218189650'
,'6285726287612'
,'6282394517916'
,'6285157128522'
,'6282196956817'
,'6281227577682'
,'6283115313346'
,'6285280165627'
,'6282297042070'
,'6289650807314'
,'6282191167862'
,'6282210467478'
,'6282319192651'
,'6288224735330']:
        if phone == '6282195195502' :
            return True
        else :
            return False
    else:
        return False
