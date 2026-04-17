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
    if param.isfromMe :
        return main_chat(param.phoneNumber, param.name, param.text, param.isfromMe)
    # return main_chat(phoneNumber, name, text, isfromMe)