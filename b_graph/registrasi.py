import re
from graph.text import Form_Identitas, Kalimat_Pembuka
from email_validator import validate_email, EmailNotValidError
from loguru import logger
from db.model_wablas import WablasIncomingMessage
from db.models import WablasIncomingMessage, User
from typing import Tuple
from wablas.send import send_simple_text

FORM_PATTERNS = {
    "nama_lengkap": r"nama\s*lengkap\s*:\s*(.*)",
    "email": r"email\s*:\s*(.*)",
    "tahun_lahir": r"tahun\s*lahir\s*:\s*(\d*)",
    "pekerjaan": r"pekerjaan\s*:\s*(.*)",
    "instansi": r"instansi.*?:\s*(.*)",
}

def extract_form_data(text: str):
    text_lower = text.lower()
    result = {}

    for field, pattern in FORM_PATTERNS.items():
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            result[field] = match.group(1).strip()
    return result

def registrasi(user: User | None, message :WablasIncomingMessage) -> Tuple[User, bool]:
    phone = message.phone
    nama_lengkap = user.nama_lengkap if user is not None else message.pushName
    stop = False

    if user is not None :
        stop = True

    if user is None:
        check_iden = False
        extract_form = {}

        if 'nama lengkap' in message.message.lower():
            check_iden = True
            extract_form = extract_form_data(message.message)
        
        if not check_iden: 
            send_simple_text(phone, Kalimat_Pembuka.format(nama = nama_lengkap))
            send_simple_text(phone, Form_Identitas)
            stop = True
        else:
            try:
                logger.info(extract_form)
                
                # 2. Gunakan .get() agar terhindar dari KeyError jika regex gagal menangkap field
                email_input = extract_form.get('email', '').strip()
                nama_input = extract_form.get('nama_lengkap', '').strip()
                pekerjaan_input = extract_form.get('pekerjaan', '').strip()
                instansi_input = extract_form.get('instansi', '').strip()
                tahun_lahir_input = extract_form.get('tahun_lahir', '').strip()

                # 3. Validasi isian kosong dengan variabel yang sudah diamankan
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
                
                # CATATAN: Pastikan fungsi validate_email me-raise error jika tidak valid.
                # Jika fungsi Anda hanya me-return boolean, ubah menjadi:
                # if not validate_email(email_input): raise EmailNotValidError("email format salah")
                validate_email(email_input)
                
                user = User.create(
                    nama = message.pushName,
                    notelp = phone,
                    email = email_input,
                    nama_lengkap = nama_input,
                    pekerjaan = pekerjaan_input,
                    instansi = instansi_input,
                    tahun_lahir = int(tahun_lahir_input),
                )
           
            except EmailNotValidError as e:
                logger.info(f"Error Email: {e}")
                send_simple_text(phone, "Mohon maaf email tidak sesuai format\ncontoh : abc@contoh.com")
                stop = True
            except ValueError as e:
                logger.info(f"Error Tahun: {e}")
                send_simple_text(phone, "Mohon maaf tahun lahir tidak sesuai format\ncontoh : 1995")
                stop = True
            except Exception as e:
                logger.info(f"Error Umum: {e}")
                send_simple_text(phone, "Mohon mengisi identitas dengan menyalin form secara lengkap")
                stop = True
    
     
    return user, stop