from langchain_ollama import OllamaLLM
from dotenv import load_dotenv, find_dotenv
import os
from google import genai
import asyncio
from _global import logger
import asyncio

load_dotenv(find_dotenv()) 

async def llm_query(prompt: str, api_key_s, config) :
    client = genai.Client(api_key=api_key_s)

    model = "gemma-4-31b-it"

    response = await client.aio.models.generate_content(
        model=model, contents=prompt, config=config
    )
    if response and response.text:
        return response.text
    else:
        raise Exception("Terjadi kesalahan")
