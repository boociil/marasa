from db.models import get_or_create_active_session
from wablas.send import send_menu, send_simple_text
from _global import shared_cache
from db.model_wablas import WablasIncomingMessage
from db.models import ChatSession, User
from typing import Tuple
from b_graph.check_working import check_work_status
from _global import logger

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os

async def set_layanan(user: User | None, message :WablasIncomingMessage) -> Tuple[ChatSession, bool, bool]:
    phone = message.phone
    session, baru_status = await get_or_create_active_session(phone)

    logger.info('set_layanan')
    logger.info(f'kirim_menu__{session.id}__{phone}')

    stop = False
    nama_lengkap = user.nama_lengkap if user is not None else message.pushName

    work_status, text = await check_work_status()

    if baru_status or session.layanan == 0 :
        if not shared_cache.get(f'kirim_menu__{session.id}__{phone}', False) :
            await send_menu(phone, work_status, nama_lengkap)
            shared_cache.set(f'kirim_menu__{session.id}__{phone}', True)
            stop = True
        return session, baru_status, stop
    
    if message.text.startswith('Menu Layanan <~1️⃣ Konsultasi Statistik'):
        if not baru_status :
            session.is_done = True
            await session.aio_save()
            session, baru_status = await get_or_create_active_session(phone)

        session.layanan = 1
        await session.aio_save()    

        if work_status :
            await send_simple_text(phone, f"Mohon tunggu sebentar kak *{nama_lengkap}* ⏳. Saya teruskan pesan ini ke petugas kami agar segera dibantu. 😊")
        else :
            await send_simple_text(phone, f"Mohon maaf kak *{nama_lengkap}* ⏳, admin sedang tidak aktif karena di luar jam kerja . 🙏")    

        
    elif message.text.startswith('Menu Layanan <~2️⃣ Pengaduan'):
        if not baru_status :
            session.is_done = True
            await session.aio_save()
            session, baru_status = await get_or_create_active_session(phone)
        session.layanan = 2
        await session.aio_save()

        await send_simple_text(phone, f"Mohon maaf atas ketidaknyamanannya Bapak/Ibu *{nama_lengkap}* 🙏🏻. Silakan sampaikan pengaduan Anda.")
    elif message.text.startswith('Menu Layanan <~3️⃣ Chat AI Statistik 🤖'):
        if not baru_status :
            session.is_done = True
            await session.aio_save()
            session, baru_status = await get_or_create_active_session(phone)
        session.layanan = 3
        await session.aio_save()

        await send_simple_text(phone, f"Halo 👋 Saya asisten virtual yang siap membantu Anda. Silakan sampaikan kebutuhan atau pertanyaan Anda.")
    else:
        pass

    return session, baru_status, stop
