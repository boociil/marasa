import argparse
import os
import shutil
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from src.get_embedding_function import get_embedding_function
from langchain_chroma import Chroma
import hashlib


CHROMA_PATH = "chroma"
DATA_PATH = "data/pdf"


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
    docs = loader.load()

    # inject file hash ke metadata tiap page
    for doc in docs:
        source = doc.metadata.get("source")
        doc.metadata["file_hash"] = get_file_hash(source)

    return docs


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
        embedding_function=get_embedding_function()
    )

    # ambil hash lama di DB
    existing_hashes = get_existing_file_hashes(db)

    # group chunk berdasarkan source file
    chunks_by_source = {}
    for chunk in chunks:
        source = chunk.metadata["source"]
        chunks_by_source.setdefault(source, []).append(chunk)

    new_chunks = []

    for source, file_chunks in chunks_by_source.items():
        new_hash = file_chunks[0].metadata["file_hash"]
        old_hash = existing_hashes.get(source)

        # 🔥 jika file baru atau berubah → hapus lama + reingest
        if old_hash != new_hash:
            print(f"♻️ File changed or new: {source}")
            delete_documents_by_source(db, source)
            new_chunks.extend(file_chunks)
        else:
            print(f"✅ File unchanged: {source}")

    # hitung chunk id
    new_chunks = calculate_chunk_ids(new_chunks)

    if new_chunks:
        print(f"👉 Adding documents: {len(new_chunks)} chunks")
        ids = [c.metadata["id"] for c in new_chunks]
        db.add_documents(new_chunks, ids=ids)
    else:
        print("🎉 Database already up-to-date")


def calculate_chunk_ids(chunks):

    # This will create IDs like "data/monopoly.pdf:6:2"
    # Page Source : Page Number : Chunk Index

    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source")
        page = chunk.metadata.get("page")
        current_page_id = f"{source}:{page}"

        # If the page ID is the same as the last one, increment the index.
        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        # Calculate the chunk ID.
        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id

        # Add it to the page meta-data.
        chunk.metadata["id"] = chunk_id

    return chunks


def clear_database():
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

def get_file_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_existing_file_hashes(db: Chroma):
    data = db.get(include=["metadatas"])
    hashes = {}

    for meta in data["metadatas"]:
        source = meta.get("source")
        file_hash = meta.get("file_hash")
        if source and file_hash:
            hashes[source] = file_hash

    return hashes

def delete_documents_by_source(db: Chroma, source: str):
    results = db.get(where={"source": source})
    ids = results["ids"]

    if ids:
        print(f"🗑️ Removing old chunks for: {source} ({len(ids)} chunks)")
        db.delete(ids=ids)

