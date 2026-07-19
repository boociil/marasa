from langchain_ollama import OllamaLLM
from dotenv import load_dotenv, find_dotenv
from google import genai
from _global import logger
import asyncio

load_dotenv(find_dotenv()) 

async def llm_query(prompt: str, api_key_s: str, config) -> str:
    try:
        client = genai.Client(api_key=api_key_s)
        model = "gemma-4-31b-it"
        # logger.info('llm_query start')
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=model, 
                contents=prompt, 
                config=config
            ),
            timeout=60.0
        )
        
        if response and response.text:
            # logger.info('llm_query end (Success)')
            return response.text
        else:
            # Seringkali error terjadi karena prompt diblokir oleh sistem keamanan Google
            logger.error(f"llm_query end (Gagal: Respons text kosong). Detail respons: {response}")
            raise Exception("Model tidak mengembalikan teks, kemungkinan terkena safety filter.")
            
    except Exception as e:
        # BARI INI SANGAT PENTING: Akan mencetak apa penyebab aslinya (misal: API_KEY_INVALID)
        logger.exception(f"llm_query FATAL ERROR: {str(e)}")
        raise e
    
async def llm_query_(prompt: str, api_key_s: str) -> str:
    try:
        client = genai.Client(api_key=api_key_s)
        model = "gemma-4-31b-it"
        # logger.info('llm_query start')
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=model, 
                contents=prompt, 
            ),
            timeout=60.0
        )
        
        if response and response.text:
            # logger.info('llm_query end (Success)')
            return response.text
        else:
            # Seringkali error terjadi karena prompt diblokir oleh sistem keamanan Google
            logger.error(f"llm_query end (Gagal: Respons text kosong). Detail respons: {response}")
            raise Exception("Model tidak mengembalikan teks, kemungkinan terkena safety filter.")
            
    except Exception as e:
        # BARI INI SANGAT PENTING: Akan mencetak apa penyebab aslinya (misal: API_KEY_INVALID)
        logger.exception(f"llm_query FATAL ERROR: {str(e)}")
        raise e