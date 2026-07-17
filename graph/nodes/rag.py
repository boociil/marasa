from graph.rag.retriever import  get_rag_data_arr, get_rag_data_table_arr, get_rag_rilis_publikasi, get_ddgs_arr
from graph.text import LLM_PROMPT
from graph.llm import llm_query
from db.model_rag import QuestionModel, RagPublikasiBRS, RagData, RagRilisPublikasi, AnswerModel, DDGS
from dotenv import load_dotenv, find_dotenv
import os
import json
import unicodedata
from langchain_community.tools import DuckDuckGoSearchResults
from _global import logger
from aiolimiter import AsyncLimiter

rate_limit = AsyncLimiter(3, 60)

import asyncio

load_dotenv(find_dotenv()) 

async def pecah_question_and_transform_untuk_rag(state) :
    history = "\n".join(item for item in state["chat_history"] if item.startswith("user"))

    new_chat = "\n".join(state["new_chat"])

    prompt = f"""Anda adalah Agen Ekstraksi Pertanyaan dan Pengoptimal Kueri tingkat lanjut untuk sistem Retrieval-Augmented Generation (RAG).

TUJUAN:
Analisis teks yang diberikan (dengan mempertimbangkan riwayat percakapan), ekstrak semua pertanyaan eksplisit maupun implisit, lalu LANGSUNG TERJEMAHKAN istilah di dalam pertanyaan tersebut menggunakan Terminologi Resmi BPS (ke dalam field `pertanyaan_asli`). Kemudian hasilkan variasi kueri pencarian yang dioptimalkan dan array kata kunci (keyword) spesifik untuk memaksimalkan relevansi dokumen yang ditarik oleh sistem.

PANDUAN WAJIB TERMINOLOGI STATISTIK (BPS):
Setiap istilah awam atau singkatan di bawah ini WAJIB diubah ke istilah resmi BPS, baik di dalam ekstraksi pertanyaan (`pertanyaan_asli`), `kueri_pencarian`, maupun `keyword`:
A. Ekonomi Makro & Kesejahteraan:
    - Pertumbuhan ekonomi / kemajuan ekonomi ➔ PDRB, Laju Pertumbuhan Ekonomi
    - Daya beli / pengeluaran warga ➔ Pengeluaran Konsumsi Rumah Tangga, Pengeluaran per Kapita
    - Inflasi / harga naik ➔ Inflasi, Indeks Harga Konsumen
    - Kemiskinan / orang miskin ➔ Persentase Penduduk Miskin, Garis Kemiskinan
    - Kesenjangan / ketimpangan ➔ Gini Ratio, Distribusi Pendapatan
B. Ketenagakerjaan:
    - Pengangguran / susah cari kerja / TPT ➔ Tingkat Pengangguran Terbuka
    - Ketersediaan tenaga kerja / TPAK ➔ Angkatan Kerja, Tingkat Partisipasi Angkatan Kerja
    - Orang kerja ➔ Penduduk Bekerja
    - Perguruan Tinggi / Lulusan Perguruan Tinggi / Kampus ➔  Pendidikan Tinggi (Diploma I/II/III/Akademi dan Universitas)
C. Sosial, Pendidikan, Kesehatan:
    - Kualitas hidup / kesejahteraan / IPM ➔ Indeks Pembangunan Manusia
    - Umur panjang / kesehatan / AHH ➔ Angka Harapan Hidup
    - Pendidikan / putus sekolah / RLS / HLS ➔ Rata-rata Lama Sekolah, Harapan Lama Sekolah
D. Pertanian & Kesejahteraan Petani:
    - Kesejahteraan petani / NTP / NTUP ➔ Nilai Tukar Petani, Nilai Tukar Usaha Pertanian
    - Hasil panen / produksi tani ➔ Luas Panen, Produktivitas, Produksi
E. Bahasa Sektor / Lapangan Usaha Eksekutif:
    - Industri / pabrik / manufaktur ➔ PDRB Lapangan Usaha Industri Pengolahan
    - Pariwisata / hotel / restoran / pengunjung ➔ PDRB Lapangan Usaha Penyediaan Akomodasi dan Makan Minum, Tingkat Penghunian Kamar, Jumlah Wisatawan
    - Tambang / galian ➔ PDRB Lapangan Usaha Pertambangan dan Penggalian
    - Jual beli / pasar / perdagangan ➔ PDRB Lapangan Usaha Perdagangan Besar dan Eceran
    - Bangunan / proyek / infrastruktur ➔ PDRB Lapangan Usaha Konstruksi
    - Sektor tani / pertanian ➔ PDRB Lapangan Usaha Pertanian, Kehutanan, dan Perikanan
E. Wilayah:
    - 6 Kabupaten ➔ Majene, Polewali Mandar, Mamasa, Mamuju, Pasangkayu, Mamuju Tengah
F. Lainnya :
    - DDA ➔ Daerah Dalam Angka

ATURAN EKSTRAKSI PERTANYAAN:
1. Pertahankan bahasa asli dari pertanyaan.
2. Gabungkan pertanyaan jika memiliki maksud yang sama atau duplikat.
3. Pertanyaan yang diekstrak tidak selalu harus diakhiri dengan tanda tanya (?).
4. PECAH PERTANYAAN MULTI-INDIKATOR (SANGAT PENTING): Jika teks meminta beberapa indikator atau topik yang tidak saling berhubungan (misalnya: "data x, y, dan z"), Anda WAJIB memecahnya menjadi beberapa objek JSON (pertanyaan) yang terpisah untuk masing-masing indikator.
5. Jangan sertakan penjelasan, kecuali penjelasan tersebut adalah bagian krusial dari konteks pertanyaan.
6. Gunakan riwayat percakapan untuk melengkapi konteks kalimat (abaikan jika tidak relevan dengan input saat ini).


ATURAN EKSTRAKSI KATA KUNCI (KEYWORD):
1. Ekstrak kata kunci utama yang substansial dan searchable (seperti nama variabel, indikator, konsep, wilayah, entitas, atau periode data).
2. Setiap item dalam array keyword HARUS tepat 1 (satu) kata tunggal. Jika ada frasa penting (misal: "pertumbuhan ekonomi"), pecah menjadi kata-kata penyusunnya yang bermakna ("pertumbuhan", "ekonomi").
3. Pastikan kata kunci periode waktu/tahun dimasukkan ke dalam array jika ada atau jika ditambahkan secara otomatis.
4. ABAIKAN kata kuantitas, agregasi, kata percakapan, atau kata tanya (seperti: "jumlah", "total", "angka", "berapa", "kapan", "siapa", "tolong", "carikan").
5. Keyword tidak boleh singkatan

ATURAN OPTIMASI KUERI PENCARIAN RAG:
1. Buat minimal 1 kueri pencarian mandiri (standalone) untuk setiap pertanyaan. Kueri tidak boleh bergantung pada referensi kata ganti ("itu", "dia").
2. LARANGAN KERAS VARIASI SUPERFISIAL: JANGAN PERNAH membuat variasi kueri yang dasarnya adalah kalimat yang sama namun hanya ditambahi kata pengisi/basa-basi di depannya (seperti: "data", "angka", "persentase", "statistik", "jumlah", atau "daftar").
3. PENANGANAN VARIABEL HUBUNGAN: Jika teks mencari HUBUNGAN antar variabel (misal: "hubungan a dan b"), jadikan SATU objek JSON dengan variasi kueri yang mencakup masing-masing variabel dan kueri hubungan keduanya. JANGAN dipecah jika konteksnya adalah korelasi/hubungan.
4. KONTEKS WILAYAH & WAKTU OTOMATIS: Jika pertanyaan mencari data dan TIDAK ada konteks wilayah, WAJIB tambahkan kata "Sulawesi Barat". Jika TIDAK ada konteks waktu, WAJIB tambahkan tahun terbaru "2025" dan "2026".
5. EKSPANSI TERMINOLOGI STATISTIK (BPS): Terjemahkan bahasa awam ke istilah resmi BPS, dan perluas singkatan:
   A. Ekonomi Makro & Kesejahteraan:
      - Pertumbuhan ekonomi / kemajuan ekonomi ➔ PDRB, Laju Pertumbuhan Ekonomi
      - Daya beli / pengeluaran warga ➔ PKRT (Pengeluaran Konsumsi Rumah Tangga), Pengeluaran per Kapita
      - Inflasi / harga naik ➔ IHK (Indeks Harga Konsumen)
      - Kemiskinan / orang miskin ➔ Persentase Penduduk Miskin (P0), Garis Kemiskinan
      - Kesenjangan / ketimpangan ➔ Gini Ratio, Distribusi Pendapatan
   B. Ketenagakerjaan:
      - Pengangguran / susah cari kerja ➔ TPT (Tingkat Pengangguran Terbuka)
      - Ketersediaan tenaga kerja ➔ Angkatan Kerja, TPAK (Tingkat Partisipasi Angkatan Kerja)
      - Orang kerja ➔ Penduduk Bekerja
      - Perguruan Tinggi / Lulusan Perguruan Tinggi / Kampus ➔  Pendidikan Tinggi (Diploma I/II/III/Akademi dan Universitas)
   C. Sosial, Pendidikan, Kesehatan:
      - Kualitas hidup / kesejahteraan ➔ IPM (Indeks Pembangunan Manusia)
      - Umur panjang / kesehatan ➔ AHH (Angka Harapan Hidup)
      - Pendidikan / putus sekolah ➔ RLS (Rata-rata Lama Sekolah), HLS (Harapan Lama Sekolah)
   D. Pertanian & Kesejahteraan Petani:
      - Kesejahteraan petani ➔ NTP (Nilai Tukar Petani), NTUP (Nilai Tukar Usaha Pertanian)
      - Hasil panen / produksi tani ➔ Luas Panen, Produktivitas, Produksi
   E. Bahasa Sektor / Lapangan Usaha Eksekutif:
      - Industri / pabrik / manufaktur ➔ PDRB Lapangan Usaha Industri Pengolahan
      - Pariwisata / hotel / restoran / pengunjung ➔ PDRB Lapangan Usaha Penyediaan Akomodasi dan Makan Minum, Tingkat Penghunian Kamar (TPK), Jumlah Wisatawan
      - Tambang / galian ➔ PDRB Lapangan Usaha Pertambangan dan Penggalian
      - Jual beli / pasar / perdagangan ➔ PDRB Lapangan Usaha Perdagangan Besar dan Eceran
      - Bangunan / proyek / infrastruktur ➔ PDRB Lapangan Usaha Konstruksi
      - Sektor tani / pertanian ➔ PDRB Lapangan Usaha Pertanian, Kehutanan, dan Perikanan
6. JANGAN mencoba menjawab pertanyaan, tugas Anda HANYA membuat kueri.

ATURAN OUTPUT (SANGAT KETAT):
- Anda HANYA boleh merespons dengan format array JSON yang valid.
- TIDAK BOLEH ada teks tambahan, penjelasan, atau blok markdown di luar array JSON. Output harus murni teks JSON.
- Jika tidak ada pertanyaan yang ditemukan sama sekali dalam teks, kembalikan array kosong: []

FORMAT JSON YANG DIHARAPKAN:
[
  {{
    "pertanyaan_asli": "Teks pertanyaan yang telah dirapikan",
    "kueri_pencarian": [
      "variasi kueri kata kunci panjang 1",
      "variasi kueri kata kunci panjang 2"
    ],
    "keyword": [
      "keyword1",
      "keyword2"
    ]
  }}
]

CONTOH SALAH (Jangan Lakukan Ini):
[
  {{
    "pertanyaan_asli": "Jumlah x?",
    "kueri_pencarian": ["jumlah x Sulawesi Barat 2025 2026", "total x Sulawesi Barat 2025 2026", "x Sulawesi Barat 2025 2026"],
    "keyword": ["x"]
  }}
]

[
  {{
    "pertanyaan_asli": "data angka x ke atas menurut kabupaten/kota tahun 2019-2024",
    "kueri_pencarian": ["angka x ke atas Sulawesi Barat 2019-2024", "persentase penduduk x ke atas kabupaten kota Sulawesi Barat 2019-2024", "statistik x Sulawesi Barat 2019-2024"],
    "keyword": ["angka", "x", "persentase", "x", "statistik", "x"]
  }}
]

(ALASAN SALAH: Ketiga kueri di atas pada dasarnya adalah kalimat yang persis sama, hanya ditambahi kata filler seperti "angka", "persentase penduduk", dan "statistik pendidikan". Ini sangat tidak berguna untuk sistem RAG. Keyword juga kehilangan konteks tahun dan wilayah).


CONTOH BENAR:
[
  {{
    "pertanyaan_asli": "data TPAK dan persentase kemiskinan",
    "kueri_pencarian": [
      "Tingkat Partisipasi Angkatan Kerja TPAK Sulawesi Barat 2025 2026",
      "persentase penduduk miskin kemiskinan Sulawesi Barat 2025 2026"
    ],
    "keyword": [
      "TPAK",
      "kemiskinan",
      "Sulawesi",
      "Barat",
      "2025",
      "2026"
    ]
  }},
  {{
    "pertanyaan_asli": "hubungannya data TPAK dan persentase kemiskinan dengan pertumbuhan ekonomi",
    "kueri_pencarian": [
      "Tingkat Partisipasi Angkatan Kerja TPAK dengan Laju Pertumbuhan Ekonomi PDRB",
      "korelasi persentase kemiskinan terhadap pertumbuhan ekonomi",
      "hubungannya data TPAK dan persentase kemiskinan Sulawesi Barat 2025 2026"
    ],
    "keyword": [
      "TPAK",
      "kemiskinan",
      "pertumbuhan",
      "ekonomi",
      "Sulawesi",
      "Barat",
      "2025",
      "2026"
    ]
  }}
]

CONTOH BENAR (PERTANYAAN MULTI-INDIKATOR DIPECAH):
User: "Saya butuh data kemiskinan dan infrastruktur jalan kabupaten kota."
[
  {{
    "pertanyaan_asli": "data kemiskinan kabupaten kota",
    "kueri_pencarian": [
      "Persentase Penduduk Miskin P0 Garis Kemiskinan kabupaten kota Sulawesi Barat 2025 2026",
      "tingkat kesejahteraan masyarakat prasejahtera Sulawesi Barat",
      "kemiskinan P0 miskin kabupaten kota 2025 2026"
    ],
    "keyword": ["kemiskinan", "kabupaten", "kota", "Sulawesi", "Barat", "2025", "2026"]
  }},
  {{
    "pertanyaan_asli": "data infrastruktur jalan kabupaten kota",
    "kueri_pencarian": [
      "kondisi panjang jalan menurut tingkat kewenangan kabupaten kota Sulawesi Barat 2025 2026",
      "aksesibilitas aspal permukaan jalan rusak baik Sulawesi Barat",
      "infrastruktur jalan kabupaten kota 2025 2026"
    ],
    "keyword": ["infrastruktur", "jalan", "kabupaten", "kota", "Sulawesi", "Barat", "2025", "2026"]
  }}
]

=== INPUT ===
Riwayat Percakapan:
{history if history.strip() != "" else "-"}

Teks Pengguna:
{new_chat}
"""
    extract_rag_json = []

    attmpt = 1
    while True:
        if attmpt == 4 :
            raise Exception("Terjadi kesalahan")
        try :
            extract_rag = await llm_query(prompt, os.getenv('Whatsapp7600_02_Api_KEY'),config={
                "response_mime_type": "application/json",
                "response_json_schema":  {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pertanyaan_asli": {
                                "type": "string",
                            },
                            "kueri_pencarian": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                            },
                            "keyword": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                            }
                        },
                    }
                },
            })
            extract_rag_json = json.loads(extract_rag.replace("```",""))
            break
        except Exception as e:
            logger.info(e)
            await asyncio.sleep(10)
            attmpt += 1
    logger.info(extract_rag_json)
    ques_arr = []
    for item in extract_rag_json:
        kueri_pencarian = []
        for item_kuri in item['kueri_pencarian']:
            if item_kuri.strip() != "" :
                kueri_pencarian.append(item_kuri.strip())
        ques_arr.append(QuestionModel(ques=item['pertanyaan_asli'], rag_ques=kueri_pencarian, keyword=item['keyword']))
    state["question"] = ques_arr
    return state

async def rag_search(state):
    for index, item in enumerate(state['question']) :
        query = state["question"][index].rag_ques
        keywords = state["question"][index].keyword

        ddgs_,docs_pdf, docs_table, docs_rilis_publikasi = await asyncio.gather(
            get_ddgs_arr(query),
            get_rag_data_arr(query, keywords, 5),
            get_rag_data_table_arr(query, keywords, 5),
            get_rag_rilis_publikasi(query, keywords, 5)
        )

        state["question"][index].ddgs = ddgs_
        state["question"][index].rag_publikasi_brs = docs_pdf
        state["question"][index].rag_data = docs_table
        state["question"][index].rag_rilis_publikasi = docs_rilis_publikasi

    return state

def append_chunk(chunks_arr, chunks, text, max_chars=6000):
    text = text + "\n\n"

    if not chunks:
        return text

    if len(chunks) + len(text) <= max_chars:
        return chunks + text

    chunks_arr.append(chunks)
    return text

async def rag_rerank(state):
    logger.info(f'rag_rerank : {len(state['question'])}')
    for index, item__ in enumerate(state['question']) :
        ques = state["question"][index].ques

        chunks_arr = []
        chunks = ""

        for item in state["question"][index].rag_data :
            chunks = append_chunk(chunks_arr, chunks, item.print())
        for item in state["question"][index].rag_publikasi_brs :
            chunks = append_chunk(chunks_arr, chunks, item.print())
        for item in state["question"][index].rag_rilis_publikasi :
            chunks = append_chunk(chunks_arr, chunks, item.print())
        for item in state["question"][index].ddgs :
            chunks = append_chunk(chunks_arr, chunks, item.print())
        chunks_arr.append(chunks)

        id_keep_rag = []
        for chunks in chunks_arr : 
            # logger.info(chunks)
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
            
            found = False
            attmpt = 1
            while True:
                if attmpt > 4 :
                    raise Exception("Terjadi kesalahan")
                try :
                    async with rate_limit:
                        id_keep_rag_txt = await llm_query(prompt, os.getenv('Whatsapp7600_03_Api_KEY'),config={
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

                        id_keep_rag_ = json.loads(id_keep_rag_txt.replace("```",""))
                        logger.info(id_keep_rag_)
                        id_keep_rag += id_keep_rag_
                        break
                except Exception as e:
                    logger.info(e)
                    await asyncio.sleep(20)
                    attmpt += 1

            for item_score in id_keep_rag :
                if item_score['score'] == 100 :
                    found = True
            if found :
                break
        id_keep_rag_dict = {}
        for item in id_keep_rag :
            id_keep_rag_dict[item['id']] = {'jawaban' : item['jawaban'], 'score': item['score']}

        for item in state["question"][index].rag_publikasi_brs :
            if item.id in id_keep_rag_dict :
                if id_keep_rag_dict[item.id]['score'] > 1 :
                    state["question"][index].rag_publikasi_brs_output.append(
                        RagPublikasiBRS( 
                            id = item.id,
                            bps_id = item.bps_id,
                            type = item.type,
                            title = item.title, 
                            halaman= item.halaman,
                            content = item.content,
                            rl_date = item.rl_date,
                            file_path= item.file_path,
                            score= item.score,
                            jawaban= id_keep_rag_dict[item.id]['jawaban']
                        )
                    )
        
        for item in state["question"][index].rag_data :
            if item.id in id_keep_rag_dict :
                if id_keep_rag_dict[item.id]['score'] > 1 :
                    state["question"][index].rag_data_output.append(
                        RagData( 
                            id = item.id,
                            judul = item.judul,
                            url= item.url,
                            content = item.content,
                            score= item.score,
                            jawaban= id_keep_rag_dict[item.id]['jawaban']
                        )
                    )
        for item in state["question"][index].rag_rilis_publikasi :
            if item.id in id_keep_rag_dict :
                state["question"][index].rag_rilis_publikasi_output.append(
                    RagRilisPublikasi( 
                        id = item.id,
                        tipe = item.tipe, 
                        bps_id  = item.bps_id, 
                        rl_date = item.rl_date, 
                        content = item.content, 
                        score= item.score,
                    )
                )
        for item in state["question"][index].ddgs :
            if item.id in id_keep_rag_dict :
                state["question"][index].ddgs_output.append(
                    DDGS( 
                        id = item.id,
                        snippet = item.snippet,
                        title = item.title,
                        link = item.link,
                    )
                )

        id_keep_rag.sort(key=lambda item: item["score"], reverse=True)
        id_keep_rag_iddd = []
        for item in id_keep_rag :
            id_keep_rag_iddd.append(item['id'])

        state["question"][index].urutan_rag  = id_keep_rag_iddd
        logger.info(f'{index} : {ques}')
        logger.info(id_keep_rag)
    return state

async def rag_answer(state):
    logger.info('rag_answer')
    for index, item in enumerate(state['question']) :
        ques = state["question"][index].ques

        chunks = ""
        chunks_dict = {}
        for item in state["question"][index].rag_publikasi_brs_output :
            chunks_dict[item.id] = item
        for item in state["question"][index].rag_data_output :
            chunks_dict[item.id] = item
        for item in state["question"][index].rag_rilis_publikasi_output :
            chunks_dict[item.id] = item
        for item in state["question"][index].ddgs_output :
            chunks_dict[item.id] = item

        for id_ in  state["question"][index].urutan_rag : 
            if id_ in chunks_dict :
                chunks += chunks_dict[id_].print()+'\n\n'
        
        logger.info(chunks)
        if len(state["question"][index].rag_publikasi_brs_output) + len(state["question"][index].rag_data_output) == 0:
            state["question"][index].answer.append(AnswerModel(type="text", text="Maaf, kami belum menemukan data yang sesuai."))
            continue
        
        prompt = LLM_PROMPT.format(
            context=chunks,
            question=ques
        )

        hasil = None
        attmpt = 1
        while True:
            if attmpt > 4 :
                raise Exception("Terjadi kesalahan")
            try :
                hasil_txt = await llm_query(prompt,  os.getenv('Whatsapp7600_04_Api_KEY'),config={
                    "response_mime_type": "application/json",
                    "response_json_schema":  {
                        
                            "type": "object",
                            "properties": {
                                "jawaban": {
                                    "type": "string",
                                },
                                "sitasi": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    },
                                }
                            },
                        
                    },
                })

                hasil = json.loads(hasil_txt.replace("```",""))
                break
            except Exception as e:
                logger.info(e)
                await asyncio.sleep(10)
                attmpt += 1
        logger.info(hasil)
        for item_sitasi in hasil['sitasi'] :
            if isinstance(chunks_dict[item_sitasi], RagPublikasiBRS) :
                state["question"][index].answer.append(AnswerModel(type="file", text=f"{chunks_dict[item_sitasi].title}, Hal {chunks_dict[item_sitasi].halaman}", file_path=chunks_dict[item_sitasi].file_path))
        
        state["question"][index].answer.append(AnswerModel(type="text", text=hasil['jawaban'], sitasi=hasil['sitasi']))
        
    return state

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
       