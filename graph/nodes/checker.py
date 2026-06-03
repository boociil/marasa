from dotenv import load_dotenv, find_dotenv
from graph.llm import llm_query
import os
from _logger import logger

load_dotenv(find_dotenv()) 

async def checker(state):
    if len(state['chat_history']) == 0 :
        state['session_done'] = False
        return state
    last_user_msg = state['new_chat'][len(state['new_chat']) - 1]
    prompt = f"""Analisis pesan user berikut: "{last_user_msg}"
Tentukan kategori pesan tersebut berdasarkan konteks layanan Badan Pusat Statistik (BPS). Jawab HANYA dengan satu kata kunci berikut:
PUAS: Jika user menyatakan terima kasih, sudah cukup, atau mengakhiri percakapan tanpa pertanyaan tambahan.
TANYA: Jika user bertanya tentang data statistik, metodologi, atau layanan BPS lainnya.
ADMIN: Jika user secara eksplisit meminta untuk berbicara dengan manusia, admin, CS, atau staf.
OFF: Jika pesan di luar konteks layanan BPS, bersifat ofensif, tidak relevan (spam), atau melanggar kebijakan keamanan."""
    hasil = "TANYA"
    while True:
        logger.info(prompt)
        respomse_text = await llm_query(prompt, os.getenv('Whatsapp7600_01_Api_KEY'), {})
        logger.info(respomse_text)
        if respomse_text.upper() in ['PUAS', 'TANYA', 'ADMIN', 'OFF'] :
            hasil = respomse_text
            break

    state['check'] = hasil
    return state
       
        