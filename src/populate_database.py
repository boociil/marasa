import os
import shutil
import argparse
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from src.get_embedding_function import get_embedding_function
from langchain_chroma import Chroma


CHROMA_PATH = os.getenv('CHROMA_PATH')
DATA_PATH = os.getenv('DATA_PATH')

def main():

    # # Check if the database should be cleared (using the --clear flag).
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--reset", action="store_true", help="Reset the database.")
    # args = parser.parse_args()
    # if args.reset:
    #     print("✨ Clearing Database")
    #     clear_database()

    # Create (or update) the data store.
    documents = load_documents()
    chunks = split_documents(documents)
    add_to_chroma(chunks)

def load_documents():
    loader = PyPDFDirectoryLoader(DATA_PATH)
    return loader.load()

def split_documents(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)

def add_to_chroma(chunks: list[Document]):
    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=get_embedding_function() # Pastikan fungsi ini ada
    )

    # Identifikasi file apa saja yang ada di batch ingest kali ini
    sources_to_ingest = set([chunk.metadata.get("source") for chunk in chunks])

    # Logika Overwrite: Hapus data lama berdasarkan path (source) jika ada di DB
    for source in sources_to_ingest:
        existing_items = db.get(where={"source": source})
        if len(existing_items["ids"]) > 0:
            # print(f"♻️ Overwriting: {source} (Deleting {len(existing_items['ids'])} old chunks)")
            db.delete(ids=existing_items["ids"])
        else:
            print(f"🆕 Adding new file: {source}")

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