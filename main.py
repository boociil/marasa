from fastapi import FastAPI
from pydantic import BaseModel
# from src.query_data import query_rag
from src.graph.main import main_chat

app = FastAPI()

class Param(BaseModel):
   jid: str
   phoneNumber: str
   name: str
   text: list[str]
   isfromMe: bool



@app.post("/")
def read_root(param: Param):
    # print("main")
    # print(param.phoneNumber)
    if param.phoneNumber in ['6281342774989', '6281399152242', '6282344852209', '6285255178499', '6285342419813', '6281218189650']:
        return main_chat(param.phoneNumber, param.name, param.text, param.isfromMe)
    else :
        return []
    # return main_chat(phoneNumber, name, text, isfromMe)

@app.post("/health_check")
def health_check():
    print("health_check")
    return["a", "b"]