from db.model_rag import RagPublikasiBRS, RagData, RagRilisPublikasi, DDGS
from graph.llm import llm_query
import asyncio
from _global import logger
from dotenv import load_dotenv, find_dotenv
from aiolimiter import AsyncLimiter
import json
import re
import os

load_dotenv(find_dotenv()) 


API_KEYS = [
    os.getenv('Whatsapp7600_03_Api_KEY', ''),
    os.getenv('Whatsapp7600_05_Api_KEY', ''),
    os.getenv('Whatsapp7600_06_Api_KEY', ''),
    os.getenv('Whatsapp7600_07_Api_KEY', ''),
    os.getenv('Whatsapp7600_08_Api_KEY', ''),
]

class APIKeyPool:
    def __init__(self, api_keys):
        self.queue = asyncio.Queue()
        for key in api_keys:
            if key and key != "":  # Pastikan key tidak kosong
                # Pasangkan setiap key dengan limiternya masing-masing (2 request per 60 detik)
                self.queue.put_nowait({
                    "key": key,
                    "limiter": AsyncLimiter(2, 60) 
                })

GLOBAL_KEY_POOL = APIKeyPool(API_KEYS)


def clean_json_string(text: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    return cleaned

def append_chunk(chunks_arr, chunks, text, max_chars=10000):
    text = text + "\n\n"

    if not chunks:
        return text

    if len(chunks) + len(text) <= max_chars:
        return chunks + text

    chunks_arr.append(chunks)
    return text

async def return_key_after_cooldown(key_pool, data, delay):
    await asyncio.sleep(delay)
    key_pool.queue.put_nowait(data)

async def fetch_chunk_score(ques, chunks, key_pool):
    prompt =f""""Kamu adalah sistem Penilai Relevansi Dokumen dan Ekstraktor Jawaban untuk pipeline RAG..

    Tugas:
    1. Evaluasi dan pilih `knowledge chunks` yang benar-benar relevan untuk menjawab pertanyaan.
    2. Berikan skor relevansi (relevance score) untuk setiap chunk yang dipilih. (0-100)
    3. Ekstrak atau susun jawaban untuk pertanyaan pengguna yang HANYA didasarkan pada masing-masing chunk yang terpilih tersebut.
    4. Jawaban harus lengkap dan jangan di perpendek
    5. Perhatikan pertanyaan dan periode data yang ditanyakan saat menghasilkan jawaban

    Aturan Evaluasi, Filtering, & Scoring:
    - Pilih chunk yang berisi fakta yang bisa langsung dipakai untuk menjawab pertanyaan.
    - Hapus chunk yang hanya sedikit berkaitan.
    - Hapus chunk yang tidak membantu menjawab pertanyaan.
    - Hapus chunk jika informasi tidak relevan atau sama dengan chunk sebelumnya
    - Jika tidak ada yang relevan, kembalikan list kosong.
    - Perhatikan periode data saat memilih chunk
    - JANGAN menjawab pertanyaan.
    - Output HARUS JSON saja, tanpa penjelasan.
    - OUTPUT CUKUP Array dari id pengetahuan
    - Urutkan dari yang paling relevan
    - Jangan memilih chunck yang formatnya daftar isi, daftar gambar, daftar tabel, dan daftar pustaka
    - Berikan skor relevansi dari skala 1 hingga 100 (100 = Sangat relevan dan langsung menjawab inti pertanyaan, 1 = Hampir tidak relevan).
    

    Aturan Output (Sangat Ketat):
    - Output HARUS berupa JSON array murni.
    - JANGAN berikan teks pengantar, penutup, atau penjelasan apa pun di luar JSON.
    - JANGAN gunakan blok kode markdown (seperti ```json ... ```). Langsung keluarkan format JSON-nya saja.

    Format JSON yang diharapkan:
    [
        {{
            "id": "string_id_1",
            "score": 9,
            "jawaban": "Tuliskan jawaban spesifik untuk pertanyaan pengguna yang ditarik HANYA dari chunk ini."
        }},
        {{
            "id": "string_id_2",
            "score": 47,
            "jawaban": "Tuliskan jawaban spesifik untuk pertanyaan pengguna yang ditarik HANYA dari chunk ini."
        }}
    ]

    Pertanyaan:
    {ques}

    Daftar knowledge chunks:
    {chunks}"""
            
    attmpt = 1
    while True:
        if attmpt > 4 :
            raise Exception("Terjadi kesalahan")
        
        api_data = await key_pool.queue.get()
        api_key = api_data["key"]
        limiter = api_data["limiter"]

        try :
            async with limiter:
                id_keep_rag_txt = await llm_query(prompt, api_key,config={
                    "response_mime_type": "application/json",
                    "response_json_schema":  {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                },
                                "score": {
                                    "type": "number",
                                },
                                "jawaban": {
                                    "type": "string",
                                },
                            },
                        }
                    },
                })
                id_keep_rag_ = json.loads(clean_json_string(id_keep_rag_txt))
                key_pool.queue.put_nowait(api_data)
                
                return id_keep_rag_
        except asyncio.CancelledError:
            # JIKA TASK DIBATALKAN KARENA SKOR 100 KETEMU, KEMBALIKAN KEY KE POOL
            key_pool.queue.put_nowait(api_data)
            raise
        except Exception as e:
            logger.info(f"Attempt {attmpt} failed: {e}")
            # PERBAIKAN: Hukum API key yang error dengan cooldown 20 detik di background.
            # Jangan block loop utama dengan `await asyncio.sleep(20)`
            asyncio.create_task(return_key_after_cooldown(key_pool, api_data, 20))
            attmpt += 1
            await asyncio.sleep(2)  # Jeda sedikit sebelum antre token lagi


                