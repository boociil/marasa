from db.model_rag import RagPublikasiBRS, RagData, RagRilisPublikasi, DDGS
from graph.llm import llm_query, llm_query_
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
    prompt =f""""Kamu adalah sistem Penilai Relevansi Dokumen dan Ekstraktor Jawaban untuk pipeline RAG.

    Tugas Utama:
    1. Evaluasi dan pilih `knowledge chunks` yang secara spesifik relevan untuk menjawab pertanyaan pengguna.
    2. Berikan skor relevansi (1-100) untuk setiap chunk terpilih.
    3. Ekstrak dan susun jawaban HANYA berdasarkan informasi yang ada di dalam masing-masing chunk terpilih. Jawaban harus lengkap dan tidak diperpendek.

    Aturan Evaluasi, Filtering, & Scoring (SANGAT KETAT):
    - PENCOCOKAN SEMANTIK: Pertanyaan awam yang bermaksud menanyakan sebuah metrik harus dianggap valid jika data memuat metrik statistik yang menjawab maksud pertanyaan tersebut secara akurat.
    - SYARAT SKOR 100: Skor 100 HANYA boleh diberikan jika chunk memenuhi KETIGA syarat berikut secara absolut:
        a) Indikator/topik di chunk SECARA SEMANTIK SAMA/EKUIVALEN dengan maksud indikator yang ditanyakan pengguna.
        b) Periode waktu/tahun data di chunk SESUAI dengan periode yang ditanyakan.
        c) Chunk tersebut mampu menjawab pertanyaan secara utuh dan sempurna.
    - Kurangi skor secara proporsional jika chunk dapat menjawab sebagian, namun informasinya kurang utuh.
    - Hapus (jangan masukkan ke output) chunk yang:
        a) Maksud indikatornya secara fundamental berbeda sama sekali atau berbeda periode waktu dengan yang ditanyakan.
        b) Hanya memuat daftar isi, daftar gambar, daftar tabel, atau daftar pustaka.
        c) Berisi informasi yang redundan/sama persis dengan chunk yang sudah dinilai sebelumnya.
        d) Tidak memuat fakta yang bisa dipakai untuk menjawab pertanyaan.
    - Jika tidak ada satupun chunk yang relevan, kembalikan array kosong: []
    - Urutkan hasil output dari skor yang paling tinggi (paling relevan) ke yang paling rendah.

    Aturan Ekstraksi Jawaban:
    - JANGAN menggunakan pengetahuan (prior knowledge) di luar teks chunk.
    - Susun jawaban secara spesifik dan selengkap mungkin berdasarkan teks pada chunk tersebut.

    Aturan Output (Wajib Dipatuhi):
    - Output HARUS murni berupa JSON array.
    - JANGAN tambahkan teks pengantar, penutup, atau penjelasan apa pun.
    - JANGAN gunakan blok kode markdown (seperti ```json atau ```). Langsung keluarkan format teks JSON-nya saja.

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


async def fetch_chunk_jawaban(ques, chunks, key_pool):
    prompt =f""""Kamu adalah sistem Penilai Relevansi Dokumen dan Ekstraktor Jawaban untuk pipeline RAG.

    Tugas Utama:
    1. Evaluasi `knowledge chunks` yang diberikan untuk memastikan relevansinya dengan pertanyaan.
    2. Ekstrak dan susun satu jawaban komprehensif HANYA berdasarkan informasi dari chunk yang paling relevan.

    Aturan Evaluasi & Filtering (SANGAT KETAT):
    - PENCOCOKAN SEMANTIK: Pertanyaan awam tentang sebuah metrik dianggap valid jika data memuat metrik statistik yang menjawab maksud pertanyaan secara akurat.
    - RELEVANSI TINGGI: Gunakan chunk yang secara semantik ekuivalen dan periode waktu/tahunnya sesuai dengan yang ditanyakan.
    - Abaikan chunk yang:
        a) Maksud indikator atau periode waktunya berbeda sama sekali.
        b) Hanya memuat daftar isi, daftar gambar, daftar tabel, atau daftar pustaka.
        c) Tidak memuat fakta yang bisa dipakai untuk menjawab pertanyaan.
    - Jika tidak ada satupun chunk yang relevan, kembalikan tesk kosong: ""

    Aturan Ekstraksi Jawaban:
    - JANGAN menggunakan pengetahuan (prior knowledge) di luar teks chunk.
    - Susun jawaban secara spesifik, jelas, dan selengkap mungkin berdasarkan teks pada chunk. Jika ada beberapa chunk yang relevan, gabungkan informasinya dengan rapi.

    Aturan Output (Wajib Dipatuhi):
    - Output HARUS murni berupa teks biasa (plain text).
    - JANGAN format output sebagai JSON atau array.
    - JANGAN tambahkan teks pengantar (seperti "Berikut adalah jawabannya:"), penutup, atau penjelasan sistem apa pun. Langsung berikan jawaban akhirnya.

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
                relevan_teks = await llm_query_(prompt, api_key)
                key_pool.queue.put_nowait(api_data)
                
                return relevan_teks
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