import os
from langchain_core.documents import Document
from populate.get_embedding_function import get_embedding_function
from langchain_chroma import Chroma
from dotenv import load_dotenv, find_dotenv
import os
import json
from html import unescape
import re
from datetime import datetime

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
        page_content_ = f""""Judul : {item['title']}

abstract
{item['abstract']}"""
        
        metadata_ = {
            'tipe': "publication",
            'id': item["pub_id"],
            'rl_date': item['rl_date'],
            'updt_date': item['updt_date'],
        }
        ids.append(item['rl_date']+'---'+str(item["pub_id"]))
        documents.append(Document(page_content=page_content_, metadata=metadata_))

    data_pressrelease_id = {}
    data_pressrelease = []
    for item in data['pressrelease'] :
        if not item["brs_id"] in data_pressrelease_id :
            data_pressrelease_id[item["brs_id"]] = len(data_pressrelease)
            data_pressrelease.append(item)
        else :
            index_awal = data_pressrelease_id[item["brs_id"]]
            rl_awal = datetime.strptime(data_pressrelease[index_awal]['rl_date'], "%Y-%m-%d")
            rl_item = datetime.strptime(item['rl_date'], "%Y-%m-%d")
            updt_awal = datetime.strptime(data_pressrelease[index_awal]['updt_date'], "%Y-%m-%d") if data_pressrelease[index_awal]['updt_date'] is not None else None
            updt_item = datetime.strptime(item['updt_date'], "%Y-%m-%d") if item['updt_date'] is not None else None

            if rl_awal == rl_item and updt_awal == updt_item :
                pass
            elif rl_item < rl_awal :
                pass
            elif rl_item > rl_awal :
                data_pressrelease[data_pressrelease_id[item["brs_id"]]] = item
            else:
                if updt_item is None:
                    pass
                elif updt_awal is None:
                    data_pressrelease[data_pressrelease_id[item["brs_id"]]] = item
                elif updt_item < updt_awal :
                    pass
                elif updt_item > updt_awal :
                    data_pressrelease[data_pressrelease_id[item["brs_id"]]] = item


    print(f"Panjang awal : {len(data['pressrelease'])}")
    print(f"Panjang awal : {len(data_pressrelease)}")
    for item in data_pressrelease :
        decoded = unescape(item['abstract'])

        # Ambil isi dalam tag <li>
        items = re.findall(r"<li>(.*?)</li>", decoded, re.DOTALL)

        # Hapus tag HTML lain seperti <i>
        cleaned = [
            re.sub(r"<.*?>", "", item).strip()
            for item in items
        ]

        # Gabungkan jadi raw text
        raw_text = "\n".join(f"- {item}" for item in cleaned)

        page_content_ = f""""Judul : {item['title']}
        
abstract
{ raw_text }"""
        
        metadata_ = {
            'tipe': "pressrelease",
            'id': item["brs_id"],
            'rl_date': item['rl_date'],
            'updt_date': item['updt_date'],
        }
        ids.append(item['rl_date']+'---'+str(item["brs_id"]))
        documents.append(Document(page_content=page_content_, metadata=metadata_))

    print(f"Process {len(documents)} Dokumen")
    db.add_documents(
        documents,
        ids=ids,
    )
