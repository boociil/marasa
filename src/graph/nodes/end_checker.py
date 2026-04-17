from dotenv import load_dotenv, find_dotenv
from google import genai
import os

load_dotenv(find_dotenv()) 

def end_checker(state) -> bool:
    if len(state['chat_history']) == 0 :
        state['is_done'] = False
        return state
    last_user_msg = state['new_chat'][len(state['new_chat']) - 1]

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"""
User message:
"{last_user_msg}"

Apakah user sudah puas dan ingin mengakhiri percakapan?
Jawab hanya: YES atau NO
"""

    while True:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", contents=prompt
        )

        if response and response.text:
            state['is_done'] = response.text == "YES"
            return state