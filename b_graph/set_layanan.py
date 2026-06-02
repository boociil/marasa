from db.models import get_or_create_active_session
from wablas.send import send_menu, send_simple_text
from cache import shared_cache
from db.model_wablas import WablasIncomingMessage
from db.models import WablasIncomingMessage, ChatSession, User
from typing import Tuple
from b_graph.check_working import check_work_status

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os

def set_layanan(user: User | None, message :WablasIncomingMessage) -> Tuple[ChatSession, bool, bool]:
    phone = message.phone
    session, baru_status = get_or_create_active_session(phone)

    stop = False
    nama_lengkap = user.nama_lengkap if user is not None else message.pushName

    work_status, text = check_work_status()

    if not baru_status :
        if shared_cache.get(f'kirim_menu_{phone}', False) :
            send_menu(phone, work_status, nama_lengkap)
            shared_cache.set(f'kirim_menu_{phone}', True)
            stop = True
        return
    
    if message.text == '1️⃣ Konsultasi Statistik':
        if not baru_status :
            session.is_done = True
            session.save()
            session, baru_status = get_or_create_active_session(phone)

        session.layanan = 1
        session.save()    

        if work_status :
            send_simple_text(phone, f"Mohon tunggu sebentar kak *{nama_lengkap}* ⏳. Saya teruskan pesan ini ke petugas kami agar segera dibantu. 😊")
        else :
            send_simple_text(phone, f"Mohon maaf kak *{nama_lengkap}* ⏳, admin sedang tidak aktif karena di luar jam kerja . 🙏")    

        
    elif message.text == '2️⃣ Pengaduan':
        if not baru_status :
            session.is_done = True
            session.save()
            session, baru_status = get_or_create_active_session(phone)
        session.layanan = 2
        session.save()

        send_simple_text(phone, f"Mohon maaf atas ketidaknyamanannya Bapak/Ibu *{nama_lengkap}* 🙏🏻. Silakan sampaikan pengaduan Anda.")
    elif message.text == '3️⃣ Chat AI Statistik 🤖':
        if not baru_status :
            session.is_done = True
            session.save()
            session, baru_status = get_or_create_active_session(phone)
        session.layanan = 3
        session.save()

        send_simple_text(phone, f"Halo 👋 Saya asisten virtual yang siap membantu Anda. Silakan sampaikan kebutuhan atau pertanyaan Anda.")
    else:
        pass

    return session, baru_status, stop
