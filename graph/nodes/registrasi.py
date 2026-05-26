from db.models import User, get_user_by_phone
import re
from graph.text import Form_Identitas, Kalimat_Pembuka
from email_validator import validate_email, EmailNotValidError

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
def registrasi(state):
    user = get_user_by_phone(state['notelp'])

    if user is None:
        check_iden = False
        extract_form = {}
        for item in state['new_chat']:
            if 'nama lengkap' in item.lower():
                check_iden = True
                extract_form = extract_form_data(item)
        
        if not check_iden: 
            state["sis_answer"] = [
                Kalimat_Pembuka.format(nama = state['nama']),
                Form_Identitas
            ]
            state['is_done'] = True
        else:
            try:
                print(extract_form)
                
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
                    jid = state['jid'],
                    nama = state['nama'],
                    notelp = state['notelp'],
                    email = email_input,
                    nama_lengkap = nama_input,
                    pekerjaan = pekerjaan_input,
                    instansi = instansi_input,
                    tahun_lahir = int(tahun_lahir_input),
                )
           
            except EmailNotValidError as e:
                print(f"Error Email: {e}")
                state["sis_answer"] = [
                    "Mohon maaf email tidak sesuai format"
                ]
                state['is_done'] = True
            except ValueError as e:
                print(f"Error Tahun: {e}")
                state["sis_answer"] = [
                    "Mohon maaf tahun lahir tidak sesuai format"
                ]
                state['is_done'] = True
            except Exception as e:
                print(f"Error Umum: {e}")
                state["sis_answer"] = [
                    "Mohon mengisi identitas dengan menyalin form secara lengkap"
                ]
                state['is_done'] = True
    else:
        state['nama_lengkap'] = user.nama_lengkap
        state['user_is_db'] = True