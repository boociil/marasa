from graph.rag.retriever import  get_rag_data_arr, get_content_rag_data_by_halaman, get_rag_data_table_arr
from graph.text import LLM_PROMPT
from graph.llm import llm_query, llm_query_answer
from db.model_rag import QuestionModel, RagPublikasiBRS, RagData, AnswerModel, DDGS
from dotenv import load_dotenv, find_dotenv
import os
import uuid
import json
import unicodedata
from google.genai.types import Tool, GenerateContentConfig
from langchain_community.tools import DuckDuckGoSearchResults
from _logger import logger

load_dotenv(find_dotenv()) 

async def pecah_question_and_transform_untuk_rag(state) :
    history = "\n".join(item for item in state["chat_history"] if item.startswith("user"))

    new_chat = "\n".join(state["new_chat"])

    prompt = f"""
Anda adalah Agen Ekstraksi Pertanyaan dan Pengoptimal Kueri tingkat lanjut untuk sistem Retrieval-Augmented Generation (RAG).

Tujuan Anda:
Analisis teks yang diberikan (dengan mempertimbangkan riwayat percakapan), ekstrak semua pertanyaan eksplisit maupun implisit, dan hasilkan beberapa variasi kueri pencarian yang dioptimalkan untuk masing-masing pertanyaan tersebut guna memaksimalkan relevansi dokumen (seperti publikasi, tabel statis, atau metadata) yang akan ditarik oleh sistem.
Tambahkan pula array keyword yang harus ada pada saat query

Optimasi Pertanyaan asli :
- Jika pertanyaan asli mencari data dan TIDAK ada konteks wilayah, tambahkan kata kunci "Sulawesi Barat".
- Jika pertanyaan asli mencari data dan TIDAK ada konteks waktu, tambahkan tahun terbaru "2025" dan "2026".

Aturan Ekstraksi Pertanyaan & Kata Kunci:
- Pertahankan konteks utama pertanyaan.
- Pertanyaan yang diekstrak tidak selalu harus diakhiri dengan tanda tanya (?).
- Jangan sertakan penjelasan, kecuali penjelasan tersebut adalah bagian krusial dari konteks pertanyaan.
- Gabungkan pertanyaan jika memiliki maksud yang sama atau duplikat.
- Pertahankan bahasa asli pertanyaan.
- Gunakan riwayat percakapan untuk melengkapi konteks kalimat, namun abaikan jika tidak relevan dengan teks pengguna saat ini.
- Ekstrak kata kunci (keyword) utama dari pertanyaan. Setiap item dalam array kata kunci HARUS berupa tepat 1 (satu) kata tunggal. Jika terdapat frasa penting (misal: "pertumbuhan ekonomi"), pecah menjadi kata-kata penyusunnya yang bermakna ("pertumbuhan", "ekonomi").
- Ekstrak kata kunci (keyword) utama dari pertanyaan. Kata kunci harus berupa istilah substansial yang searchable (seperti nama variabel, indikator, konsep, wilayah, atau entitas).
- ABAIKAN kata-kata kuantitas, agregasi, atau kata tanya (seperti: "jumlah", "total", "angka", "berapa", "kapan", "siapa").
- usahakan keyword 1 kata

Aturan Optimasi Kueri Pencarian RAG:
- Buat minimal 1 kueri pencarian mandiri (standalone) untuk setiap pertanyaan yang diekstrak.
- Buat lebih dari 1 kueri pencarian jika ada beberapa indikator yang dicari (Misal: jika mencari "hubungan variabel A dan B", buat kueri untuk A, kueri untuk B, dan kueri untuk hubungan keduanya).
- Pertahankan bahasa asli.
- Perluas kata kunci (gunakan sinonim atau kepanjangan dari singkatan, misal: TPAK menjadi Tingkat Partisipasi Angkatan Kerja).
- Hapus kata-kata percakapan atau basa-basi (seperti "tolong", "halo", "carikan").
- Kueri harus mandiri (tidak bergantung pada referensi kata ganti seperti "itu" atau "dia").
- JANGAN mencoba menjawab pertanyaan, Anda hanya bertugas membuat kueri.
- Jika pertanyaan mencari data dan TIDAK ada konteks wilayah, tambahkan kata kunci "Sulawesi Barat".
- Jika pertanyaan mencari data dan TIDAK ada konteks waktu, tambahkan tahun terbaru "2025" dan "2026".

Aturan Output (SANGAT KETAT):
- Anda HANYA boleh merespons dalam format array JSON yang valid.
- Tidak boleh ada teks tambahan, penjelasan, atau blok *markdown* di luar JSON.
- Jika tidak ada pertanyaan yang ditemukan sama sekali dalam teks, kembalikan array kosong: []

Format JSON yang diharapkan:
[
  {{
    "pertanyaan_asli": "Teks pertanyaan yang telah dirapikan",
    "kueri_pencarian": [
      "variasi kueri kata kunci panjang 1",
      "variasi kueri kata kunci panjang 2",
      "variasi kueri kata kunci spesifik 3",
      dst..
    ]
    "keyword": [
      "keyword 1",
      "keyword 2",
      "keyword 3",
      dst..
    ]
  }}
]

contoh salah:
[{{'pertanyaan_asli': 'Jumlah x?', 'kueri_pencarian': ['jumlah x Sulawesi Barat 2025 2026', 'total x Sulawesi Barat 2025 2026', 'x Sulawesi Barat 2025 2026'], keyword: [x]}}]

salah kaerana pada dasarnya sama

contoh benar:
[
  {{
    "pertanyaan_asli": "data TPAK dan persentase kemiskinan",
    "kueri_pencarian": [
      "Tingkat Partisipasi Angkatan Kerja TPAK Sulawesi Barat 2025 2026",
      "persentase penduduk miskin kemiskinan Sulawesi Barat 2025 2026"
    ],
    keyword: ['TPAK', 'kemiskinan']
  }},
  {{
    "pertanyaan_asli": "hubungannya data TPAK dan persentase kemiskinan dengan pertumbuhan ekonomi",
    "kueri_pencarian": [
      "Tingkat Partisipasi Angkatan Kerja TPAK dengan pertumbuhan ekonomi",
      "persentase kemiskinan terhadap pertumbuhan ekonomi",
      "hubungannya data TPAK dan persentase kemiskinan"
    ]
    keyword: ['TPAK', 'pertumbuhan ekonomi']
  }}
]

=== INPUT ===
Riwayat Percakapan:
{history if history.strip() != "" else "-"}

Teks Pengguna:
{new_chat}
"""
    extract_rag_json = []

    while True:
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

        search = DuckDuckGoSearchResults(output_format="list")
        logger.info(f"site:bps.go.id {', '.join(query)}")
        results_list = search.invoke(f"site:bps.go.id {', '.join(query)}")

        for res in results_list:
            state["question"][index].ddgs.append(
                DDGS( 
                    id = str(uuid.uuid4()),
                    snippet = res['snippet'] ,
                    title = res['title'],
                    link = res['link'],
                )
            )

        docs_pdf = get_rag_data_arr(query, 5)
        sorce_page_unique = []
        for doc, _score in docs_pdf:
            bps_id = ""
            type = ""
            if 'pub_id' in doc.metadata : 
                bps_id = doc.metadata['pub_id']
                type = 'pub'
            if 'brs_id' in doc.metadata : 
                bps_id = doc.metadata['brs_id']
                type = 'brs'
            
            source_page = f"{doc.metadata['source'] } -+- {doc.metadata['page']}"
            text = doc.page_content
            if any(keyword.lower() in text.lower() for keyword in keywords):
                if source_page not in sorce_page_unique :
                    state["question"][index].rag_publikasi_brs.append(
                        RagPublikasiBRS( 
                            id = str(uuid.uuid4()),
                            bps_id = bps_id,
                            type = type,
                            title = doc.metadata['title'], 
                            halaman= int(doc.id.split(':')[-2])+1, 
                            content = get_content_rag_data_by_halaman(doc.metadata['source'], doc.metadata['page']), 
                            rl_date = doc.metadata['rl_date'], 
                            score= _score
                        )
                    )
                    sorce_page_unique.append(source_page)

        docs_table = get_rag_data_table_arr(query, 5)
        for doc, _score in docs_table:
            text = doc.page_content
            if any(keyword.lower() in text.lower() for keyword in keywords):
                state["question"][index].rag_data.append(
                    RagData( 
                        id = str(uuid.uuid4()),
                        judul = doc.metadata['judul'], 
                        url= 'https://sulbar.bps.go.id/id/statistics-table/'+doc.metadata.get("sumber", None)+'/'+doc.metadata.get("table_id", None)+'/data.html', 
                        content = doc.page_content, 
                        score= _score
                    )
                )
    return state

async def rag_rerank(state):
    for index, item in enumerate(state['question']) :
        ques = state["question"][index].ques
        chunks = ""

        for item in state["question"][index].rag_publikasi_brs :
            chunks += item.print() +'\n\n'
        for item in state["question"][index].rag_data :
            chunks += item.print() +'\n\n'
        for item in state["question"][index].ddgs :
            chunks += item.print() +'\n\n'
        logger.info(chunks)
        prompt =f""""
Kamu adalah penilai relevansi dokumen untuk sistem RAG.

Tugas:
Pilih HANYA potongan pengetahuan (knowledge chunks) yang benar-benar membantu menjawab pertanyaan.

Aturan ketat:
- Pilih chunk yang berisi fakta yang bisa langsung dipakai untuk menjawab pertanyaan.
- Hapus chunk yang hanya sedikit berkaitan.
- Hapus chunk yang tidak membantu menjawab pertanyaan.
- Hapus chunk jika informasi tidak relevan atau sama dengan chunk sebelumnya
- Jika tidak ada yang relevan, kembalikan list kosong.
- JANGAN menjawab pertanyaan.
- Output HARUS JSON saja, tanpa penjelasan.
- OUTPUT CUKUP Array dari id pengetahuan
- Urutkan dari yang paling relevan

Format JSON yang diharapkan:
[string_id]

Pertanyaan:
{ques}

Daftar knowledge chunks:
{chunks}"""
        
        # print(prompt)
        id_keep_rag =[]
        while True:
            try :
                id_keep_rag_txt = await llm_query(prompt, os.getenv('Whatsapp7600_03_Api_KEY'),config={
                    "response_mime_type": "application/json",
                    "response_json_schema":  {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                })

                id_keep_rag = json.loads(id_keep_rag_txt.replace("```",""))
                break
            except Exception as e:
                logger.info

        logger.info

        for item in state["question"][index].rag_publikasi_brs :
            if item.id in id_keep_rag :
                state["question"][index].rag_publikasi_brs_output.append(
                    RagPublikasiBRS( 
                        id = item.id,
                        bps_id = item.bps_id,
                        type = item.type,
                        title = item.title, 
                        halaman= item.halaman,
                        content = item.content,
                        rl_date = item.rl_date,
                        score= item.score,
                    )
                )
        
        for item in state["question"][index].rag_data :
            if item.id in id_keep_rag :
                state["question"][index].rag_data_output.append(
                    RagData( 
                        id = item.id,
                        judul = item.judul,
                        url= item.url,
                        content = item.content,
                        score= item.score,
                    )
                )
        for item in state["question"][index].ddgs :
            if item.id in id_keep_rag :
                state["question"][index].ddgs_output.append(
                    DDGS( 
                        id = item.id,
                        snippet = item.snippet,
                        title = item.title,
                        link = item.link,
                    )
                )
       
    return state

async def rag_answer(state):
    for index, item in enumerate(state['question']) :
        ques = state["question"][index].ques
        chunks = ""

        for item in state["question"][index].rag_publikasi_brs_output :
            chunks += item.print() +'\n\n'
        for item in state["question"][index].rag_data_output :
            chunks += item.print() +'\n\n'
        for item in state["question"][index].ddgs_output :
            chunks += item.print() +'\n\n'

        if len(state["question"][index].rag_publikasi_brs_output) + len(state["question"][index].rag_data_output) == 0:
            state["question"][index].answer.append(AnswerModel(type="text", text="Maaf, kami belum menemukan data yang sesuai."))
            continue
        
        

        if len(state["question"][index].rag_publikasi_brs_output) > 0 :
            for i, item in enumerate(state["question"][index].rag_publikasi_brs_output) :
                state["question"][index].answer.append(AnswerModel(type="file", text=f"{item.title}, Hal {item.halaman}", file_path= findImagePathPublikasiBRS(item)))


        prompt = LLM_PROMPT.format(
            context=chunks,
            question=ques
        )
        hasil = await llm_query_answer(prompt,  os.getenv('Whatsapp7600_04_Api_KEY'))
        state["question"][index].answer.append(AnswerModel(type="text", text=hasil))
        
    return state

def findImagePathPublikasiBRS(item: RagPublikasiBRS):
    if item.type == 'pub': #publikas
        title = secure_filename(item.rl_date+'-'+str(item.title))
        path_folder = os.path.join(os.getenv("IMAGES_FOLDER_Publikasi"), title.replace("/", "-"))
        path_image = os.path.join(path_folder,str(item.halaman)+'.jpg')
        return path_image
    if item.type == 'brs':
        title = secure_filename(item.rl_date+'-'+str(item.bps_id))
        path_folder = os.path.join(os.getenv("IMAGES_FOLDER_BRS"), title.replace("/", "-"))
        path_image = os.path.join(path_folder,str(item.halaman)+'.jpg')
        return path_image

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
       