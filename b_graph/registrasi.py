import re
from graph.text import Form_Identitas, Kalimat_Pembuka
from email_validator import validate_email, EmailNotValidError
from _global import logger, shared_cache
from db.model_wablas import WablasIncomingMessage
from db.models import User, ChatSession
from typing import Tuple
from wablas.send import send_simple_text

FORM_PATTERNS = {
    "nama_lengkap": r"^nama\s*lengkap\s*:\s*(.+)$",
    "email": r"^email\s*:\s*(.+)$",
    "tahun_lahir": r"^tahun\s*lahir\s*:\s*(\d+)$",
    "pekerjaan": r"^pekerjaan\s*:\s*(.+)$",
    "instansi": r"^instansi.*?:\s*(.+)$",
}

def extract_form_data(text: str):
    result = {}
    for line in text.splitlines():
        line = line.strip()

        for field, pattern in FORM_PATTERNS.items():
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                result[field] = match.group(1).strip()
                break

    return result

async def registrasi(user: User | None, session: ChatSession, message: WablasIncomingMessage) -> Tuple[User, bool, bool]:
    logger.info('registrasi')
    phone = message.phone
    nama_lengkap = user.nama_lengkap if user is not None else message.pushName
    stop = False
    send_start_layanan = False

    if user is None:
        stop = True
        if not shared_cache.get(f'kirim_regis__{session.id}__{phone}', False):
            await send_simple_text(phone, Kalimat_Pembuka.format(nama=nama_lengkap))
            await send_simple_text(phone, Form_Identitas)
            shared_cache.set(f'kirim_regis__{session.id}__{phone}', True)
        else:
            if 'nama lengkap' not in message.message.lower():
                await send_simple_text(phone, "Mohon mengisi identitas dengan menyalin form secara lengkap")
                return user, stop, send_start_layanan # Tambahan: Hentikan eksekusi jika tidak valid

            try:
                extract_form = extract_form_data(message.message)
                logger.info(extract_form)
                
                email_input = extract_form.get('email', '').strip()
                nama_input = extract_form.get('nama_lengkap', '').strip()
                pekerjaan_input = extract_form.get('pekerjaan', '').strip()
                instansi_input = extract_form.get('instansi', '').strip()
                tahun_lahir_input = extract_form.get('tahun_lahir', '').strip()

                if not email_input:
                    raise EmailNotValidError("email kosong")
                if not nama_input:
                    raise Exception("nama_lengkap kosong")
                if not pekerjaan_input:
                    raise Exception("pekerjaan kosong")
                if not instansi_input:
                    raise Exception("instansi kosong")
                if not tahun_lahir_input:
                    raise ValueError("tahun_lahir kosong")
                
                validate_email(email_input)
                
                user = await User.aio_create(
                    nama=message.pushName,
                    notelp=phone,
                    email=email_input,
                    nama_lengkap=nama_input,
                    pekerjaan=pekerjaan_input,
                    instansi=instansi_input,
                    tahun_lahir=int(tahun_lahir_input),
                )
                send_start_layanan = True
                
                stop = False 
                
            except EmailNotValidError as e:
                logger.info(f"Error Email: {e}")
                await send_simple_text(phone, "Mohon maaf email tidak sesuai format\ncontoh : abc@contoh.com")
            except ValueError as e:
                logger.info(f"Error Tahun: {e}")
                await send_simple_text(phone, "Mohon maaf tahun lahir tidak sesuai format\ncontoh : 1995")
            except Exception as e:
                await send_simple_text(phone, "Mohon mengisi identitas dengan menyalin form secara lengkap")
     
    return user, stop, send_start_layanan