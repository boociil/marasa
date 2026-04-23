from src.graph.db.models import User, get_user_by_phone
import re
from src.graph.text import Form_Identitas, Kalimat_Pembuka

FORM_PATTERNS = {
    "nama_lengkap": r"nama\s*lengkap\s*:\s*(.+)",
    "email": r"email\s*:\s*(.+)",
    "tahun_lahir": r"tahun\s*lahir\s*:\s*(\d{4})",
    "pekerjaan": r"pekerjaan\s*:\s*(.+)",
    "instansi": r"instansi.*?:\s*(.+)",
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

    if user is None :
        check_iden = False
        extract_form = {}
        for item in state['new_chat'] :
            if 'Nama Lengkap' in item :
                check_iden = True
                extract_form = extract_form_data(item)
        
        if not check_iden : 
            state["answer"] = [
                Kalimat_Pembuka.format(nama = state['nama']),
                Form_Identitas
            ]
            state['is_done'] = True
            state["is_system"] = True
        else :
            try :
                user =  User.create(
                    nama = state['nama'],
                    notelp = state['notelp'],
                    email = extract_form['email'],
                    nama_lengkap = extract_form['nama_lengkap'],
                    pekerjaan = extract_form['pekerjaan'],
                    instansi = extract_form['instansi'],
                )
            except Exception as e:
                state["answer"] = [
                    "Mohon mengisi identitas dengan menyalin form"
                ]
                state['is_done'] = True
                state["is_system"] = True
    return state