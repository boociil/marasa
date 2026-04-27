from src.graph.db.models import get_or_create_active_session, load_last_messages
from src.graph.text import menu_bps

def set_layanan(state):
    session, baru_status = get_or_create_active_session(state['notelp'])
    state["session_id"] = session.get_id()
    state["layanan_type"] = session.layanan
    state["chat_history"] = load_last_messages(session)

    if state["layanan_type"] == 0:
        number = 0
        for item in state['new_chat']:
            if item in ['1','2','3','4'] :
                number = int(item)
        session.layanan = number
        session.save()

        if number != 0 :
            state['layanan_type'] = number
            state['is_done'] = True
            if number == 1 :
                state["sis_answer"].extend([f"Mohon tunggu sebentar kak *{state['nama_lengkap']}* ⏳. Saya teruskan pesan ini ke petugas kami agar segera dibantu. 😊"])
            elif number == 2 :
                state["sis_answer"].extend([f"Mohon maaf atas ketidaknyamanannya Bapak/Ibu *{state['nama_lengkap']}* 🙏🏻. Silakan sampaikan pengaduan Anda."])
            elif number == 3 :
                state["sis_answer"].extend(["Halo 👋 Saya asisten virtual yang siap membantu Anda. Silakan sampaikan kebutuhan atau pertanyaan Anda."])
            elif number == 4 :
                state["sis_answer"].extend([f"Mohon tunggu sebentar kak *{state['nama_lengkap']}* ⏳. Saya teruskan pesan ini ke petugas kami agar segera dibantu. 😊"])
        else :
            state["sis_answer"].extend([menu_bps.format(nama = state["nama_lengkap"])])
            state['is_done'] = True
    
        
        if state['layanan_type'] == 4 :
            state['use_ai'] = True
    return state