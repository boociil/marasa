import os
import shutil
import argparse
from langchain_community.document_loaders import PyPDFDirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from populate.get_embedding_function import get_embedding_function
from langchain_chroma import Chroma
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import os
import json
import unicodedata

load_dotenv(find_dotenv()) 

CHROMA_PATH = os.getenv('CHROMA_PATH_ISI_PDF')
DATA_PATH = os.getenv('DATA_PATH')
PDF_JSON = os.getenv('PDF_JSON')
PATH_LAST = os.getenv('PATH_LAST')

def populate_pdf():

    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=get_embedding_function() # Pastikan fungsi ini ada
    )

    PATH_LAST = ""
    MULAI_ENBED = False

    if os.path.exists(os.getenv('PATH_LAST')):
        try:
            with open(os.getenv('PATH_LAST'), 'r') as f:
                PATH_LAST = str(f.read().strip())
                MULAI_ENBED = False
        except FileNotFoundError:
            nomor_baris = 0
    else : 
        MULAI_ENBED = True
        open(os.getenv('PATH_LAST'), "w").close()
    

    data = {}
    with open(PDF_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data['publication'] :
        title = secure_filename(item['rl_date']+'-'+item['title'])
        path = os.path.join(os.getenv("PDF_ALL_FOLDER_Publikasi"), title.replace("/", "-") + ".pdf")
        print(title)
        if not os.path.exists(path):
            continue

        if MULAI_ENBED :
            documents = load_documents_item(path, {
                "pub_id": item['pub_id'],
                "title": item['title'],
                "issn": item['issn'],
                "rl_date": item['rl_date'],
                "updt_date": item['updt_date'],
            })
            chunk_size_ = 800
            while True:
                try:
                    chunks = split_documents(documents, chunk_size_)
                    add_to_chroma(chunks, db)
                    print("chunk size : "+str(chunk_size_))
                    break
                except Exception as e:
                    print(e)
                    chunk_size_ = chunk_size_ - 50
            print()

            with open(os.getenv('PATH_LAST'), 'w') as f:
                f.write(str(path))
        else :
            if path == PATH_LAST :
                MULAI_ENBED = True

    for item in data['pressrelease'] :
        title = secure_filename(item['rl_date']+'-'+str(item['brs_id'])+'-'+str(item['subj']))
        path = os.path.join(os.getenv("PDF_ALL_FOLDER_BRS"), title.replace("/", "-") + ".pdf")
        if not os.path.exists(path):
            continue
        print(title)

        if MULAI_ENBED :
            documents = load_documents_item(path, {
                "brs_id": item['brs_id'],
                "subj_id": item['subj_id'],
                "subj": item['subj'],
                "subcsa_id": item['subcsa_id'],
                "subcsa": item['subcsa'],
                "title": item['title'],
                "rl_date": item['rl_date'],
                "updt_date": item['updt_date'],
            })
            chunk_size_ = 800
            while True:
                try:
                    chunks = split_documents(documents, chunk_size_)
                    add_to_chroma(chunks, db)
                    print("chunk size : "+str(chunk_size_))
                    break
                except Exception as e:
                    print(e)
                    chunk_size_ = chunk_size_ - 50
            print()

            with open(os.getenv('PATH_LAST'), 'w') as f:
                f.write(str(path))
        else :
            if path == PATH_LAST :
                MULAI_ENBED = True


def load_documents_item(pdf_path, dic_metada) :
    try:
        loader = PyPDFLoader(
            pdf_path,
            password=None,
            mode="page",
            extract_images=False,
            images_parser=None,
            headers=None,
            extraction_mode="plain",
            extraction_kwargs=None,
        )
        sub_docs = loader.load()
        for doc in sub_docs:
            doc.metadata["source"] = str(pdf_path)
            for key, value in dic_metada.items():
                doc.metadata[key] = value
        return sub_docs
    except Exception as e:
        print(e)

def load_documents():
    loader = PyPDFDirectoryLoader(DATA_PATH)
    return loader.load()

def split_documents(documents: list[Document], chunk_size_: int):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_,
        chunk_overlap=150,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)

def add_to_chroma(chunks: list[Document], db):
    # Hitung Chunk ID baru
    chunks_with_ids = calculate_chunk_ids(chunks)

    # Tambahkan semua chunk ke database
    if chunks_with_ids:
        print(f"👉 Adding documents: {len(chunks_with_ids)} chunks")
        new_ids = [c.metadata["id"] for c in chunks_with_ids]
        db.add_documents(chunks_with_ids, ids=new_ids)
    else:
        print("✅ No new documents to add.")

def calculate_chunk_ids(chunks):
    # Format ID: "path/ke/file.pdf:nomor_halaman:index_chunk"
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source")
        page = chunk.metadata.get("page")
        current_page_id = f"{source}:{page}"

        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id
        chunk.metadata["id"] = chunk_id

    return chunks

def clear_database():
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

INVALID_FILE_CHARS = '/\\?%*:|"<>' # https://en.wikipedia.org/wiki/Filename#Reserved_characters_and_words

def secure_filename(filename):
    # keep only valid ascii chars
    output = list(unicodedata.normalize("NFKD", filename))

    # special case characters that don't get stripped by the above technique
    for pos, char in enumerate(output):
        if char == '\u0141':
            output[pos] = 'L'
        elif char == '\u0142':
            output[pos] = 'l'

    # remove unallowed characters
    output = [c if c not in INVALID_FILE_CHARS else '_' for c in output]
    return "".join(output).encode("ASCII", "ignore").decode()