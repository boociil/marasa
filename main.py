from fastapi import FastAPI
from src.query_data import query_rag

app = FastAPI()


@app.get("/")
def read_root(query_text: str):
    return query_rag(query_text)