from src.graph.db.models import User, get_user_by_phone
import re
from src.graph.text import Form_Identitas, Kalimat_Pembuka
from email_validator import validate_email, EmailNotValidError

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
            state["sis_answer"] = [
                Kalimat_Pembuka.format(nama = state['nama']),
                Form_Identitas
            ]
            state['is_done'] = True
        else :
            try :

                print(extract_form)
                if extract_form['email'].strip() == "" :
                    raise EmailNotValidError("email error")
                if extract_form['nama_lengkap'].strip() == "" :
                    raise Exception("nama_lengkap error")
                if extract_form['pekerjaan'].strip() == "" :
                    raise Exception("pekerjaan error")
                if extract_form['instansi'].strip() == "" :
                    raise Exception("instansi error")
                if 'tahun_lahir' not in extract_form or extract_form['tahun_lahir'].strip() == "" :
                    raise ValueError("tahun_lahir error")
                
                validate_email(extract_form['email'].strip())
                
                user =  User.create(
                    jid = state['jid'],
                    nama = state['nama'],
                    notelp = state['notelp'],
                    email = extract_form['email'],
                    nama_lengkap = extract_form['nama_lengkap'],
                    pekerjaan = extract_form['pekerjaan'],
                    instansi = extract_form['instansi'],
                    tahun_lahir = int(extract_form['tahun_lahir'].strip()),
                )
           
            except EmailNotValidError as e:
                print(e)
                state["sis_answer"] = [
                    "Mohon maaf email tidak sesuai format"
                ]
                state['is_done'] = True
            except ValueError as e:
                print(e)
                state["sis_answer"] = [
                    "Mohon maaf tahun lahir tidak sesuai format"
                ]
                state['is_done'] = True
            except Exception as e:
                print(e)
                state["sis_answer"] = [
                    "Mohon mengisi identitas dengan menyalin form"
                ]
                state['is_done'] = True
    else :
        state['nama_lengkap'] = user.nama_lengkap
        state['user_is_db'] = True

    return state