import os
import requests
from langchain_community.document_loaders import PyPDFDirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from src.get_embedding_function import get_embedding_function
from langchain_chroma import Chroma
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import os
import json
import unicodedata
from dotenv import load_dotenv, find_dotenv

# 1. LOAD ENV (Parent Folder)
load_dotenv(find_dotenv())
API_KEY = os.getenv("API_BPS")
DOMAIN = "7600"
BASE_URL = "https://webapi.bps.go.id/v1/api"
CHROMA_PATH = os.getenv('CHROMA_PATH_TABLE')

def get_categories():
    """Mengambil semua subjek (CSA) yang tersedia"""
    url = f"{BASE_URL}/list/model/subcatcsa/domain/{DOMAIN}/key/{API_KEY}/"
    while True: 
        response = requests.get(url).json()
        if response['status'] == 'OK':
            return response['data'][1]



def get_subjects(subcat, page ):
    """Mengambil semua subjek (CSA) yang tersedia"""
    url = f"{BASE_URL}/list/model/subjectcsa/domain/{DOMAIN}/subcat/{subcat}/page/{page}/key/{API_KEY}/"
    print(url)
    while True: 
        response = requests.get(url).json()
        if response['status'] == 'OK':
            return response['data'][1], response['data'][0]['pages']
        
def get_table(subject, page):
    """Mengambil semua subjek (CSA) yang tersedia"""
    url = f"{BASE_URL}/list/model/tablestatistic/domain/{DOMAIN}/subject/{subject}/page/{page}/key/{API_KEY}/"
    print(url)
    while True: 
        response = requests.get(url).json()
        if response['data-availability'] == 'list-not-available' :
            return [], None
        if response['status'] == 'OK' and response['data-availability'] != 'list-not-available':
            return response['data'][1], response['data'][0]['pages']
        

def get_detail_table(id ):
    """Mengambil semua subjek (CSA) yang tersedia"""
    url = f"{BASE_URL}/view/model/tablestatistic/domain/{DOMAIN}/lang/ind/id/{id}/key/{API_KEY}/"
    while True: 
        response = requests.get(url).json()
        if response['status'] == 'OK':
            return response['data'][1]
        
def download_main_data():

    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=get_embedding_function() # Pastikan fungsi ini ada
    )

    pattern_data = """"Judul tabel: {judul}
Kategori: {kategori}.
Subyek: {subyek}.
Cakupan waktu: {awal} sampai {akhir}.
Jenis sumber: {sumber}."""
    

    ids=[]
    documents=[]
    metadatas=[]

    categories = get_categories()
    
    for cate in categories:
        print("cate : "+cate["title"])
        page_1 = 1
        pages_1 = 1 
        while page_1 <= pages_1: 
            subject_a, pages_1 = get_subjects(cate['subcat_id'], page_1)
            for subjec in subject_a:
                print("subjec : "+subjec["title"])
                page_2 = 1
                pages_2 = 1 
                while page_2 <= pages_2:            
                    tables, pages_2_ = get_table(subjec['sub_id'], page_2)
                    if pages_2_ is not None :
                        page_2 = pages_2_
                    for item in tables :
                        print("Table : "+item["title"])
                        tablesource = ""
                        if item['tablesource'] == '1':
                            tablesource = "Static Table"
                        elif item['tablesource'] == '2':
                            tablesource = "Dynamic Table"
                        elif item['tablesource'] == '3':
                            tablesource = "SIMDASI"

                        ids.append(str(cate['subcat_id'])+'-'+str(subjec['sub_id'])+'-'+str(item['id']))
                        documents.append(Document(page_content=pattern_data.format(
                            judul=item["title"],
                            kategori=cate["title"],
                            subyek=subjec["title"],
                            awal=item["oldest_period"],
                            akhir=item["latest_period"],
                            sumber=tablesource,
                        ), metadata={
                            'subcat_id': cate['subcat_id'],
                            'sub_id': subjec['sub_id'],
                            'table_id' : item['id']
                        }))
                    page_2 += 1
            page_1 += 1


    db.add_documents(
        documents,
        ids=ids,
    )