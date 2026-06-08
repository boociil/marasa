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

async def start_layanan(user: User | None, session :ChatSession | None) :
    logger.info("start_layanan")
    if user is None or session is None :
        return
    
    phone = user.notelp
    nama_lengkap = user.nama
    
    if session.layanan == 1 :
        await send_simple_text(phone, f"Mohon tunggu sebentar Bapak/Ibu *{nama_lengkap}* ⏳. Saya teruskan pesan ini ke petugas kami agar segera dibantu. 😊")
    elif session.layanan == 2 :
        await send_simple_text(phone, f"Mohon maaf atas ketidaknyamanannya Bapak/Ibu *{nama_lengkap}* 🙏🏻. Silakan sampaikan pengaduan Anda.")
    elif session.layanan == 3 :
        await send_simple_text(phone, f"Halo 👋 Saya asisten virtual 🤖 yang siap membantu Anda. Silakan sampaikan pertanyaan Anda.")