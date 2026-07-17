from _global import logger
from db.models import ChatSession, User
from wablas.send import send_simple_text

async def start_layanan(user: User | None, session: ChatSession | None):
    logger.info("start_layanan")
    if user is None or session is None:
        return
    
    phone = user.notelp
    # Menggunakan nama_lengkap dari database agar lebih sopan, bukan pushName WA
    nama_lengkap = user.nama_lengkap 
    
    if session.layanan == 1:
        await send_simple_text(phone, f"Mohon tunggu sebentar Bapak/Ibu *{nama_lengkap}* ⏳. Saya teruskan pesan ini ke petugas kami agar segera dibantu. 😊")
    elif session.layanan == 2:
        await send_simple_text(phone, f"Mohon maaf atas ketidaknyamanannya Bapak/Ibu *{nama_lengkap}* 🙏🏻. Silakan sampaikan pengaduan Anda.")
    elif session.layanan == 3:
        await send_simple_text(phone, f"Halo 👋 Saya asisten virtual 🤖 yang siap membantu Anda. Silakan sampaikan pertanyaan Anda.")