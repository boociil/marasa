from langchain_ollama import OllamaLLM
from dotenv import load_dotenv, find_dotenv
from langchain_core.prompts import ChatPromptTemplate
import os
from google import genai
import time

load_dotenv(find_dotenv()) 

# def llm_query(prompt: str, api_key):
#     # model = OllamaLLM(model="gemma2:2b")
    
#     model = OllamaLLM(model=os.getenv("LLM_MODEL"))
#     response_text = model.invoke(prompt)
#     return response_text


def llm_query(prompt: str, api_key_s) :
    client = genai.Client(api_key=api_key_s)

    while True:
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview", contents=prompt
            )
            if response and response.text:
                print(response.text)
                return response.text
            else:
                time.sleep(3)
        except Exception as e:
            print(e)
            time.sleep(3)
       