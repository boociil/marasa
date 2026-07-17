from db.models import get_or_create_active_session
from wablas.send import send_menu, send_simple_text
from db.model_wablas import WablasIncomingMessage
from db.models import ChatSession, User
from typing import Tuple
from b_graph.check_working import check_work_status
from _global import logger

async def set_layanan(user: User | None, message: WablasIncomingMessage) -> Tuple[ChatSession, bool, bool]:
    phone = message.phone
    session, baru_status = await get_or_create_active_session(phone)

    logger.info('set_layanan')
    logger.info(f'kirim_menu__{session.id}__{phone}__{baru_status}')

    stop = False
    send_start_layanan = False
    nama_lengkap = user.nama_lengkap if user is not None else message.pushName

    work_status, text = await check_work_status()

    if baru_status:
        await send_menu(phone, work_status, nama_lengkap)
        stop = True
    
    if '<~ 1 Konsultasi Statistik' in message.message.encode('ascii', 'ignore').decode('utf-8'):
        if not work_status:
            await send_simple_text(phone, f"Mohon maaf Bapak/Ibu *{nama_lengkap}* ⏳, admin sedang tidak aktif karena di luar jam kerja . 🙏")
            stop = True
            return session, stop, send_start_layanan
            
        if session.layanan == 1:
            session.is_done = True
            await session.aio_save()
            session, baru_status = await get_or_create_active_session(phone)
        session.layanan = 1
        await session.aio_save()    
        send_start_layanan = True
        
    elif '<~ 2 Pengaduan' in message.message.encode('ascii', 'ignore').decode('utf-8'):
        if session.layanan == 2:
            session.is_done = True
            await session.aio_save()
            session, baru_status = await get_or_create_active_session(phone)
        session.layanan = 2
        await session.aio_save()
        send_start_layanan = True
        
    elif '<~ 3 Chat AI Statistik' in message.message.encode('ascii', 'ignore').decode('utf-8'):
        if session.layanan == 3:
            session.is_done = True
            await session.aio_save()
            session, baru_status = await get_or_create_active_session(phone)
        session.layanan = 3
        await session.aio_save()
        send_start_layanan = True

    if not baru_status:
        if session.layanan == 0:
            await send_simple_text(phone, f"Untuk membantu kebutuhan Anda, silakan pilih jenis layanan terlebih dahulu 🙏")
            stop = True

    return session, stop, send_start_layanan