from dotenv import load_dotenv, find_dotenv
from src.graph.llm import llm_query
import os

load_dotenv(find_dotenv()) 

def end_checker(state) -> bool:
    if len(state['chat_history']) == 0 :
        state['session_done'] = False
        return state
    last_user_msg = state['new_chat'][len(state['new_chat']) - 1]
    prompt = f"""
User message:
"{last_user_msg}"

Apakah user sudah puas dan ingin mengakhiri percakapan?
Jawab hanya: YES atau NO
"""

    state['session_done'] = llm_query(prompt, os.getenv('Whatsapp7600_01_Api_KEY')) == "YES"
    return state
       
        