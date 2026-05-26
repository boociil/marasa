import os
from langchain_core.documents import Document
from src.get_embedding_function import get_embedding_function
from langchain_chroma import Chroma
from dotenv import load_dotenv, find_dotenv
import os
import json

load_dotenv(find_dotenv()) 

CHROMA_PATH = os.getenv('CHROMA_PATH_DAFTAR')

def populate_daftar_pdf():

    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=get_embedding_function() # Pastikan fungsi ini ada
    )
    
    data = {'publication': [], 'pressrelease': []}

    try:
        with open(os.getenv('PDF_JSON'), "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {'publication': [], 'pressrelease': []}
    except json.JSONDecodeError:
        data = {'publication': [], 'pressrelease': []}


    ids=[]
    documents=[]


    for item in data['publication'] :
        judul__ = item['title']
        abstract__ =  item['abstract']
        page_content_ = """"Judul : {judul__}
abstract
{abstract__}"""
        
        metadata_ = {
            'tipe': "publication",
            'id': item["pub_id"],
            'rl_date': item['rl_date'],
            'updt_date': item['updt_date'],
        }
        ids.append(item['rl_date']+'-|-'+item["pub_id"])
        documents.append(Document(page_content=page_content_, metadata=metadata_))
        print(page_content_)
        break

    for item in data['pressrelease'] :
        judul__ = item['title']
        abstract__ =  item['abstract']
        page_content_ = """"Judul : {judul__}
abstract
{abstract__}"""
        
        metadata_ = {
            'tipe': "pressrelease",
            'id': item["brs_id"],
            'rl_date': item['rl_date'],
            'updt_date': item['updt_date'],
        }
        ids.append(item['rl_date']+'-|-'+item["pub_id"])
        documents.append(Document(page_content=page_content_, metadata=metadata_))
        print(page_content_)
        break

    # db.add_documents(
    #     documents,
    #     ids=ids,
    # )
