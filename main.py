import os
import asyncio
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI
from dotenv import load_dotenv

from graph.main import build_graph, main_chat
from _global import logger
from db.models import (
    iddle_task_ai,
    iddle_task_konsultasi,
    ChatMessage,
    close_24_hour,
    get_active_session_not_arr,
    get_handoff_session,
    get_petugas_by_phone,
    get_user_by_phone,
)
from db.model_wablas import WablasIncomingMessage
from b_graph.set_layanan import set_layanan
from b_graph.registrasi import registrasi
from b_graph.start_layanan import start_layanan
from b_graph.handoff import (
    close_idle_handoff_sessions,
    handle_petugas_message,
    handle_user_handoff_message,
)

load_dotenv()

graph = build_graph()

###########################################################################
# GLOBAL
###########################################################################

session_in_works_id = set()

# Deduplikasi webhook
id_pesan_set = set()
id_pesan_queue = deque(maxlen=200)

ALLOWED_GROUP_NUMBERS = os.getenv(
    "ALLOWED_GROUP_NUMBERS",
    # "6282195195502"
    "6282246657077"
).split(",")


def checkHpGroup(phone: str):
    return phone in ALLOWED_GROUP_NUMBERS


def _log_background(task: asyncio.Task, label: str):
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception(f"background task gagal: {label}")


def spawn_background(coro, label: str):
    """Jalankan proses berat di background agar webhook tetap cepat."""
    task = asyncio.create_task(coro)
    task.add_done_callback(lambda t: _log_background(t, label))
    return task


###########################################################################
# DEBOUNCE
###########################################################################

@dataclass
class UserBuffer:
    chats: list = field(default_factory=list)
    version: int = 0
    task: asyncio.Task | None = None


class DebounceManager:

    def __init__(self, delay: float = 2.0):
        self.delay = delay

        self.buffers: dict[str, UserBuffer] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    #######################################################################

    def _lock(self, phone: str) -> asyncio.Lock:

        lock = self.locks.get(phone)

        if lock is None:
            lock = asyncio.Lock()
            self.locks[phone] = lock

        return lock

    #######################################################################

    async def push(self, phone: str, data):

        async with self._lock(phone):

            buf = self.buffers.get(phone)

            if buf is None:
                buf = UserBuffer()
                self.buffers[phone] = buf

            buf.chats.append(data)

            buf.version += 1
            version = buf.version

            if buf.task is not None:
                buf.task.cancel()

            buf.task = asyncio.create_task(
                self._timer(phone, version)
            )

    #######################################################################

    async def _timer(self, phone: str, version: int):

        try:

            await asyncio.sleep(self.delay)

        except asyncio.CancelledError:
            return

        async with self._lock(phone):

            buf = self.buffers.get(phone)

            if buf is None:
                return

            # task lama, abaikan
            if version != buf.version:
                return

            chats = buf.chats.copy()

            self.buffers.pop(phone, None)
            self.locks.pop(phone, None)

        await self.process(phone, chats)

    #######################################################################

    async def process(self, phone: str, chats: list):

        user = await get_user_by_phone(phone)

        for data in chats:

            try:

                session, stop, send_start_layanan = await set_layanan(
                    user,
                    data
                )

                if stop:
                    continue

                user, stop_, send_start_layanan_ = await registrasi(
                    user,
                    session,
                    data
                )

                if stop_:
                    continue

                if send_start_layanan or send_start_layanan_:
                    await start_layanan(user, session)
                    continue

                await ChatMessage.aio_create(
                    session=session,
                    role="user",
                    content=data.message,
                )

            except Exception:
                logger.exception(
                    f"Error memproses pesan {phone}"
                )

    #######################################################################

    async def shutdown(self):

        tasks = []

        for buf in self.buffers.values():

            if buf.task:
                buf.task.cancel()
                tasks.append(buf.task)

        if tasks:

            await asyncio.gather(
                *tasks,
                return_exceptions=True
            )


debounce = DebounceManager(delay=2.0)

###########################################################################
# CALLBACK
###########################################################################

def on_finish_callback(task, id_session: str):

    try:
        task.result()

    except Exception:
        logger.exception(
            f"main_chat error on session {id_session}"
        )

    finally:
        session_in_works_id.discard(id_session)

###########################################################################
# WORKER AI
###########################################################################

async def debounce_per_user_worker():

    try:

        while True:

            await asyncio.sleep(1)

            # Maksimal 4 session AI berjalan bersamaan
            if len(session_in_works_id) >= 4:
                continue

            session_to_work = await get_active_session_not_arr(
                list(session_in_works_id)
            )

            for session in session_to_work:

                session_id = session.id

                if session_id in session_in_works_id:
                    continue

                session_in_works_id.add(session_id)

                all_messages = list(
                    await ChatMessage.select()
                    .where(ChatMessage.session == session)
                    .order_by(ChatMessage.created_at)
                    .aio_execute()
                )

                all_messages.reverse()

                new_message = []
                older_message = []

                found_first_bot = False

                for item in all_messages:
                    if not found_first_bot:
                        if item.role == "user":
                            new_message.append(item.content)
                        else:
                            found_first_bot = True
                            older_message.append(f"bot : {item.content}")
                    else:
                        older_message.append(f"{item.role} : {item.content}")

                task = asyncio.create_task(
                    main_chat(
                        graph,
                        session,
                        new_message,
                        older_message,
                    )
                )

                task.add_done_callback(
                    lambda t, s_id=session_id:
                    on_finish_callback(t, s_id)
                )

    except asyncio.CancelledError:

        logger.info(
            "debounce_per_user_worker stopped."
        )


###########################################################################
# IDDLE TASK
###########################################################################

async def process_per_minute():

    try:

        while True:

            await asyncio.sleep(60)

            asyncio.create_task(
                iddle_task_ai(
                    list(session_in_works_id)
                )
            )

            asyncio.create_task(
                iddle_task_konsultasi()
            )

            asyncio.create_task(
                close_idle_handoff_sessions()
            )

    except asyncio.CancelledError:

        logger.info(
            "process_per_minute stopped."
        )


###########################################################################
# LIFESPAN
###########################################################################

@asynccontextmanager
async def lifespan(app: FastAPI):

    await close_24_hour()

    worker_ai = asyncio.create_task(
        debounce_per_user_worker()
    )

    worker_idle = asyncio.create_task(
        process_per_minute()
    )

    logger.info("Application started.")

    try:

        yield

    finally:

        logger.info("Stopping application...")

        worker_ai.cancel()
        worker_idle.cancel()

        await debounce.shutdown()

        await asyncio.gather(
            worker_ai,
            worker_idle,
            return_exceptions=True
        )

        logger.info("Application stopped.")


###########################################################################
# FASTAPI
###########################################################################

app = FastAPI(
    lifespan=lifespan
)

###########################################################################
# WEBHOOK
###########################################################################

@app.post("/")
async def wablas(data: WablasIncomingMessage):

    # Abaikan pesan yang dikirim oleh device bot sendiri.
    if data.isFromMe:
        return {"status": True}

    # Abaikan pesan group
    if data.isGroup:
        return {"status": True}

    #######################################################################
    # DEDUPLIKASI
    #######################################################################

    if data.id in id_pesan_set:
        return {"status": True}

    if len(id_pesan_queue) >= id_pesan_queue.maxlen:
        oldest = id_pesan_queue.popleft()
        id_pesan_set.discard(oldest)

    id_pesan_queue.append(data.id)
    id_pesan_set.add(data.id)

    logger.info(
        f"Incoming message [{data.phone}] : {data.message}"
    )

    #######################################################################
    # ROUTING HANDOFF PETUGAS PST
    #######################################################################

    # 1. Pengirim adalah petugas (bypass whitelist).
    petugas = await get_petugas_by_phone(data.phone)
    if petugas is not None:
        spawn_background(
            handle_petugas_message(petugas, data),
            f"petugas {data.phone}"
        )
        return {"status": True}

    # 2 & 3. Pengguna pada sesi layanan 1 (menunggu / live / manual).
    session_handoff = await get_handoff_session(data.phone)
    if session_handoff is not None:
        spawn_background(
            handle_user_handoff_message(session_handoff, data),
            f"handoff {data.phone}"
        )
        return {"status": True}

    #######################################################################
    # JALUR LAMA
    #######################################################################

    # Filter nomor yang diizinkan
    if not checkHpGroup(data.phone):
        return {"status": True}

    # Abaikan pesan kosong
    if not data.message or not data.message.strip():
        return {"status": True}

    await debounce.push(
        data.phone,
        data
    )

    return {"status": True}


###########################################################################
# HEALTH CHECK
###########################################################################

@app.get("/text")
async def text():
    return {
        "status": True,
        "active_session": len(session_in_works_id),
        "debounce_user": len(debounce.buffers),
    }