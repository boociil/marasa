from fastapi import FastAPI
from pydantic import BaseModel
# from src.query_data import query_rag
from src.graph.main import main_chat
from contextlib import asynccontextmanager
import asyncio
import requests
from dotenv import load_dotenv
import os

load_dotenv()


# Define the task to run every minute
async def every_minute_task():
    while True:
       
        # Perform your logic here
        await asyncio.sleep(60) # Sleep for 60 seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background task
    task = asyncio.create_task(every_minute_task())
    yield
    # Cancel the task on shutdown
    task.cancel()

app = FastAPI(lifespan=lifespan)

class Param(BaseModel):
   jid: str
   phoneNumber: str
   name: str
   text: list[str]
   isfromMe: bool

@app.post("/")
def read_root(param: Param):
    print("main")
    print(param)
    # print(param.phoneNumber)
    # if param.phoneNumber in ['6281342774989', '6281399152242', '6282344852209', '6285255178499', '6285342419813', '6281218189650']:
    if param.isfromMe :
        jid, answer =  main_chat(param.jid, param.phoneNumber, param.name, param.text, param.isfromMe)
        path_ori = []
        for item_answer in answer:
            if item_answer.file_path is None :
                requests.post(os.getenv('URL_JS')+"/send-message", json={'jid': jid, 'text': item_answer.text})
            else :
                if item_answer.file_path not in path_ori :
                    with open(item_answer.file_path, 'rb') as f:
                        # FORMAT: (filename, file_object, mimetype)
                        files = {
                            'image': ('image.jpg', f, 'image/jpeg') 
                        }
                        
                        requests.post(os.getenv('URL_JS')+"/send-message", data={'jid': jid, 'text': item_answer.text}, files=files)
                    path_ori.append(item_answer.file_path)
                
    else :
        return []
    # return main_chat(phoneNumber, name, text, isfromMe)

@app.post("/health_check")
def health_check():
    print("health_check")
    return["a", "b"]