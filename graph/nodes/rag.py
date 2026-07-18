from graph.rag.retriever import  get_rag_data_arr, get_rag_data_table_arr, get_rag_rilis_publikasi, get_ddgs_arr
from graph.text import LLM_PROMPT
from graph.llm import llm_query
from db.model_rag import QuestionModel, RagPublikasiBRS, RagData, RagRilisPublikasi, AnswerModel, DDGS
from dotenv import load_dotenv, find_dotenv
import os
import json
import unicodedata
from _global import logger
import asyncio
from graph.nodes.rerank import GLOBAL_KEY_POOL, fetch_chunk_score, append_chunk, clean_json_string
from itertools import zip_longest

load_dotenv(find_dotenv()) 


async def pecah_question_and_transform_untuk_rag(state) :
    history = "\n".join(item for item in state["chat_history"] if item.startswith("user"))
    new_chat = "\n".join(state["new_chat"])

    prompt = f"""Anda adalah Agen Ekstraksi Pertanyaan dan Pengoptimal Kueri tingkat lanjut untuk sistem Retrieval-Augmented Generation (RAG).

TUJUAN:
Analisis teks yang diberikan (dengan mempertimbangkan riwayat percakapan), ekstrak semua pertanyaan eksplisit maupun implisit, lalu LANGSUNG TERJEMAHKAN istilah di dalam pertanyaan tersebut menggunakan Terminologi Resmi BPS. Anda WAJIB melengkapi kalimat pada field `pertanyaan_asli` dengan konteks wilayah dan periode waktu. Kemudian hasilkan variasi kueri pencarian yang dioptimalkan dan array kata kunci (keyword) spesifik untuk memaksimalkan relevansi dokumen yang ditarik oleh sistem.

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
    - Perguruan Tinggi / Lulusan Perguruan Tinggi / Kampus ➔ Pendidikan Tinggi (Diploma I/II/III/Akademi dan Universitas)
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

ATURAN KONTEKS WILAYAH & WAKTU OTOMATIS (SANGAT PENTING):
Jika pertanyaan mencari data dan TIDAK menyebutkan konteks wilayah, Anda WAJIB menyisipkan kata "Sulawesi Barat". Jika TIDAK menyebutkan konteks waktu, Anda WAJIB menyisipkan tahun terbaru "2025" dan "2026". Aturan ini BERLAKU UNTUK KETIGA FIELD (`pertanyaan_asli`, `kueri_pencarian`, dan `keyword`).

ATURAN EKSTRAKSI PERTANYAAN (`pertanyaan_asli`):
1. Pertahankan maksud kalimat, NAMUN WAJIB sempurnakan kalimatnya dengan memasukkan terjemahan istilah resmi BPS, SERTA menyisipkan konteks wilayah ("Sulawesi Barat") dan waktu ("2025", "2026") jika tidak ada di input asli.
2. Gabungkan pertanyaan jika memiliki maksud yang sama atau duplikat.
3. Pertanyaan yang diekstrak tidak selalu harus diakhiri dengan tanda tanya (?).
4. PECAH PERTANYAAN MULTI-INDIKATOR (SANGAT PENTING): Jika teks meminta beberapa indikator atau topik yang tidak saling berhubungan (misalnya: "data x, y, dan z"), Anda WAJIB memecahnya menjadi beberapa objek JSON (pertanyaan) yang terpisah untuk masing-masing indikator.
5. Jangan sertakan penjelasan, kecuali penjelasan tersebut adalah bagian krusial dari konteks pertanyaan.
6. Gunakan riwayat percakapan untuk melengkapi konteks kalimat (abaikan jika tidak relevan dengan input saat ini).
7. Dekomposisi Indikator Turunan
   Jika indikator yang dicari merupakan hasil rasio atau perhitungan matematis dari indikator lain, otomatis buatkan juga ekstraksi untuk indikator pembentuknya.
   (Contoh: Jika target adalah "PDRB Per Kapita", maka Anda harus mengekstrak indikator utamanya, sekaligus membuat ekstraksi tambahan untuk "Total PDRB" dan "Jumlah Penduduk").

ATURAN EKSTRAKSI KATA KUNCI (`keyword`):
1. Ekstrak kata kunci utama yang substansial dan searchable (seperti nama variabel, indikator, konsep, wilayah, entitas, atau periode data).
2. Setiap item dalam array keyword HARUS tepat 1 (satu) kata tunggal. Jika ada frasa penting (misal: "pertumbuhan ekonomi"), pecah menjadi kata-kata penyusunnya yang bermakna ("pertumbuhan", "ekonomi").
3. Pastikan kata kunci wilayah (misal: "Sulawesi", "Barat") dan periode waktu/tahun ("2025", "2026") dimasukkan ke dalam array, baik yang berasal dari input asli maupun dari penambahan otomatis.
4. ABAIKAN kata kuantitas, agregasi, kata percakapan, atau kata tanya (seperti: "jumlah", "total", "angka", "berapa", "kapan", "siapa", "tolong", "carikan").
5. Keyword tidak boleh berupa singkatan, jabarkan menjadi kata tunggal penyusunnya.

ATURAN OPTIMASI KUERI PENCARIAN RAG (`kueri_pencarian`):
1. Buat minimal 1 kueri pencarian mandiri (standalone) untuk setiap pertanyaan. Kueri tidak boleh bergantung pada referensi kata ganti ("itu", "dia").
2. LARANGAN KERAS VARIASI SUPERFISIAL: JANGAN PERNAH membuat variasi kueri yang dasarnya adalah kalimat yang sama namun hanya ditambahi kata pengisi/basa-basi di depannya (seperti: "data", "angka", "persentase", "statistik", "jumlah", atau "daftar").
3. PENANGANAN VARIABEL HUBUNGAN: Jika teks mencari HUBUNGAN antar variabel (misal: "hubungan a dan b"), jadikan SATU objek JSON dengan variasi kueri yang mencakup masing-masing variabel dan kueri hubungan keduanya. JANGAN dipecah jika konteksnya adalah korelasi/hubungan.
4. Terapkan ATURAN KONTEKS WILAYAH & WAKTU OTOMATIS dan perluasan Terminologi BPS pada setiap variasi kueri.
5. JANGAN mencoba menjawab pertanyaan, tugas Anda HANYA memformat output ekstraksi kueri ke JSON.

ATURAN OUTPUT (SANGAT KETAT):
- Anda HANYA boleh merespons dengan format array JSON yang valid.
- TIDAK BOLEH ada teks tambahan, penjelasan, atau blok markdown di luar array JSON. Output harus murni teks JSON.
- Jika tidak ada pertanyaan yang ditemukan sama sekali dalam teks, kembalikan array kosong: []

FORMAT JSON YANG DIHARAPKAN:
[
  {{
    "pertanyaan_asli": "Teks pertanyaan yang telah dirapikan, dilengkapi istilah resmi BPS, konteks wilayah, dan waktu",
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

CONTOH BENAR (PENAMBAHAN KONTEKS OTOMATIS DARI INPUT PENDEK):
Input User: "data TPAK dan persentase kemiskinan"
Output:
[
  {{
    "pertanyaan_asli": "Data Tingkat Partisipasi Angkatan Kerja (TPAK) dan Persentase Penduduk Miskin di Sulawesi Barat tahun 2025 dan 2026",
    "kueri_pencarian": [
      "Tingkat Partisipasi Angkatan Kerja TPAK Sulawesi Barat 2025 2026",
      "Persentase Penduduk Miskin kemiskinan Sulawesi Barat 2025 2026"
    ],
    "keyword": [
      "Tingkat",
      "Partisipasi",
      "Angkatan",
      "Kerja",
      "Persentase",
      "Penduduk",
      "Miskin",
      "Sulawesi",
      "Barat",
      "2025",
      "2026"
    ]
  }}
]

CONTOH BENAR (PERTANYAAN MULTI-INDIKATOR DIPECAH & DILENGKAPI KONTEKS):
Input User: "Saya butuh data kemiskinan dan infrastruktur jalan kabupaten kota."
Output:
[
  {{
    "pertanyaan_asli": "Data Persentase Penduduk Miskin di kabupaten kota Sulawesi Barat tahun 2025 dan 2026",
    "kueri_pencarian": [
      "Persentase Penduduk Miskin Garis Kemiskinan kabupaten kota Sulawesi Barat 2025 2026",
      "kemiskinan penduduk miskin kabupaten kota Sulawesi Barat 2025 2026"
    ],
    "keyword": ["Persentase", "Penduduk", "Miskin", "kemiskinan", "kabupaten", "kota", "Sulawesi", "Barat", "2025", "2026"]
  }},
  {{
    "pertanyaan_asli": "Data infrastruktur jalan di kabupaten kota Sulawesi Barat tahun 2025 dan 2026",
    "kueri_pencarian": [
      "kondisi panjang jalan menurut tingkat kewenangan kabupaten kota Sulawesi Barat 2025 2026",
      "infrastruktur jalan aspal permukaan jalan rusak kabupaten kota Sulawesi Barat 2025 2026"
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
        if attmpt > 4 :
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
            extract_rag_json = json.loads(clean_json_string(extract_rag))
            break
        except Exception as e:
            logger.info(e)
            await asyncio.sleep(10)
            attmpt += 1
            
    logger.info(extract_rag_json)
    ques_arr = []
    for item in extract_rag_json:
        kueri_pencarian = []
        for item_kuri in item.get('kueri_pencarian', []):
            if item_kuri.strip() != "" :
                kueri_pencarian.append(item_kuri.strip())
        ques_arr.append(QuestionModel(ques=item.get('pertanyaan_asli', ''), rag_ques=kueri_pencarian, keyword=item.get('keyword', [])))
    state["question"] = ques_arr
    return state

async def rag_search(state):
    for index, item in enumerate(state['question']) :
        query = state["question"][index].rag_ques
        keywords = state["question"][index].keyword

        ddgs_,docs_pdf, docs_table, docs_rilis_publikasi = await asyncio.gather(
            get_ddgs_arr(query),
            get_rag_data_arr(query, keywords, 8),
            get_rag_data_table_arr(query, keywords, 8),
            get_rag_rilis_publikasi(query, keywords, 5)
        )

        state["question"][index].ddgs = ddgs_
        state["question"][index].rag_publikasi_brs = docs_pdf
        state["question"][index].rag_data = docs_table
        state["question"][index].rag_rilis_publikasi = docs_rilis_publikasi

    return state

async def rag_rerank(state):
    logger.info(f"rag_rerank : {len(state['question'])}")
    for index, item__ in enumerate(state['question']) :
        q_data = state["question"][index]
        ques = state["question"][index].ques

        chunks_arr = []
        chunks = ""

        for item_data, item_brs, item_rilis, item_ddgs in zip_longest(
            q_data.rag_data,
            q_data.rag_publikasi_brs,
            q_data.rag_rilis_publikasi,
            q_data.ddgs
        ):
            if item_data is not None:
                chunks = append_chunk(chunks_arr, chunks, item_data.print())
            
            if item_brs is not None:
                chunks = append_chunk(chunks_arr, chunks, item_brs.print())
                
            if item_rilis is not None:
                chunks = append_chunk(chunks_arr, chunks, item_rilis.print())
                
            if item_ddgs is not None:
                chunks = append_chunk(chunks_arr, chunks, item_ddgs.print())

        if chunks:
            chunks_arr.append(chunks)


        id_keep_rag = []

        key_pool = GLOBAL_KEY_POOL
        
        tasks = [
            asyncio.create_task(fetch_chunk_score(ques, c, key_pool))
            for c in chunks_arr
        ]

        # 2. Proses task yang selesai lebih dulu (as_completed)
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                id_keep_rag.extend(result)
                
                found_100 = any(item.get('score', 0) == 100 for item in result)
                
                if found_100:
                    logger.info("Skor 100 ditemukan! Membatalkan sisa request ke LLM...")
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    break
                    
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Task asinkron gagal: {e}")
                
        id_keep_rag_dict = {}
        for item in id_keep_rag :
            id_keep_rag_dict[item['id']] = {'jawaban' : item.get('jawaban', ''), 'score': item.get('score', 0)}

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
                            score = id_keep_rag_dict[item.id]['score'],
                            jawaban = id_keep_rag_dict[item.id]['jawaban']
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
                            score = id_keep_rag_dict[item.id]['score'],
                            jawaban = id_keep_rag_dict[item.id]['jawaban']
                        )
                    )
                    
        for item in state["question"][index].rag_rilis_publikasi :
            if item.id in id_keep_rag_dict :
                if id_keep_rag_dict[item.id]['score'] > 1 :
                    state["question"][index].rag_rilis_publikasi_output.append(
                        RagRilisPublikasi( 
                            id = item.id,
                            tipe = item.tipe, 
                            bps_id  = item.bps_id, 
                            rl_date = item.rl_date, 
                            content = item.content, 
                            score = id_keep_rag_dict[item.id]['score'], # FIX 4
                        )
                    )
                
        for item in state["question"][index].ddgs :
            if item.id in id_keep_rag_dict :
                if id_keep_rag_dict[item.id]['score'] > 1 :
                    state["question"][index].ddgs_output.append(
                        DDGS( 
                            id = item.id,
                            snippet = item.snippet,
                            title = item.title,
                            link = item.link,
                            score = id_keep_rag_dict[item.id]['score'],
                            jawaban = id_keep_rag_dict[item.id]['jawaban']
                        )
                    )

        id_keep_rag.sort(key=lambda item: item.get("score", 0), reverse=True)
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
        if (len(state["question"][index].rag_publikasi_brs_output) + 
                len(state["question"][index].rag_data_output) + 
                len(state["question"][index].rag_rilis_publikasi_output) + 
                len(state["question"][index].ddgs_output)) == 0:
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
                hasil = json.loads(clean_json_string(hasil_txt))
                break
            except Exception as e:
                logger.info(e)
                await asyncio.sleep(10)
                attmpt += 1
                
        logger.info(hasil)
        
        # FIX 6: Hindari KeyError jika model berhalusinasi menghasilkan ID sitasi yang tidak valid
        for item_sitasi in hasil.get('sitasi', []) :
            if item_sitasi in chunks_dict and isinstance(chunks_dict[item_sitasi], RagPublikasiBRS) :
                state["question"][index].answer.append(AnswerModel(type="file", text=f"{chunks_dict[item_sitasi].title}, Hal {chunks_dict[item_sitasi].halaman}", file_path=chunks_dict[item_sitasi].file_path))
        
        state["question"][index].answer.append(AnswerModel(type="text", text=hasil.get('jawaban', ''), sitasi=hasil.get('sitasi', [])))
        
    return state

INVALID_FILE_CHARS = '/\\?%*:|"<>'

def secure_filename(filename):
    output = list(unicodedata.normalize("NFKD", filename))
    for pos, char in enumerate(output):
        if char == '\u0141':
            output[pos] = 'L'
        elif char == '\u0142':
            output[pos] = 'l'
    output = [c if c not in INVALID_FILE_CHARS else '_' for c in output]
    return "".join(output).encode("ASCII", "ignore").decode()