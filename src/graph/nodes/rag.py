from src.graph.rag.retriever import get_rag_data, get_rag_data_arr, get_rag_data_table, get_rag_data_table_arr
from src.graph.text import LLM_PROMPT
from src.graph.llm import llm_query, llm_query_answer
from src.graph.state import QuestionModel, RagPublikasiBRS, RagData, AnswerModel, DDGS
from dotenv import load_dotenv, find_dotenv
import os
import uuid
import json
import unicodedata
from google.genai.types import Tool, GenerateContentConfig
from langchain_community.tools import DuckDuckGoSearchResults

load_dotenv(find_dotenv()) 

async def pecah_question_and_transform_untuk_rag(state) :
    history = "\n".join(item for item in state["chat_history"] if item.startswith("user"))

    new_chat = "\n".join(state["new_chat"])

    prompt = f"""
Anda adalah Agen Ekstraksi Pertanyaan dan Pengoptimal Kueri tingkat lanjut untuk sistem Retrieval-Augmented Generation (RAG).

Tujuan Anda:
Analisis teks yang diberikan (mempertimbangkan riwayat percakapan), ekstrak semua pertanyaan eksplisit maupun implisit, dan hasilkan beberapa variasi kueri pencarian yang dioptimalkan untuk masing-masing pertanyaan tersebut guna memaksimalkan relevansi dokumen (seperti publikasi, tabel statis, atau metadata) yang akan ditarik.

Aturan Ekstraksi Pertanyaan:
- Jangan kehilangan konteks utama pertanyaan
- Pertanyaan bisa tampa tanda ? / tanya
- Tanpa penjelasan, kecual jika sebagai konteks utama pertanyaan.
- Tidak boleh ada teks tambahan.
- Pertahankan bahasa asli.
- Hapus duplikat.
- Jika beberapa pertanyaan dapat digabung, maka gabung
- perhatikan Riwayat percakapan namun kalo tidak relevan hilangkan


Aturan Optimasi Kueri Pencarian RAG:
- Buat minimal 1  kueri pencarian yang mandiri (standalone) untuk setiap pertanyaan yang diekstrak
- lebih dari 1 kuari pencarian jika ada beberapa indikator yang dicari (misalnya hubunggan variabel a dan b, maka masing-masing a dan b)
- Pertahankan bahasa asli
- Jangan kehilangan konteks utama
- Perluas konteks dan kata kunci
- Buat agar mandiri
- Hapus kata-kata percakapan
- JANGAN menjawab pertanyaan
- Jumlah hasil harus sama dengan jumlah pertanyaan
- Jangan memperbanyak pertanyaan
- Jika menayakan data dan tidak ada konteks wilayah tambahkan sulawesi barat
- Jika menayakan data dan tidak ada konteks waktu maka tambahkan waktu terbaru (2025, 2026)

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
      "variasi kueri kata kunci panjang 2 beserta wilayah dan tahun jika data",
      "variasi kueri kata kunci spesifik 3"
    ]
  }}
]

=== INPUT ===
Riwayat Percakapan:
{history if history.strip() != "" else "-"}

Teks Pengguna:
{new_chat}
"""
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
                    }
                },
            }
        },
    })

    print(extract_rag)
    extract_rag = json.loads(extract_rag.replace("```",""))
    
    ques_arr = []
    for item in extract_rag:
        ques_arr.append(QuestionModel(ques=item['pertanyaan_asli'], rag_ques=item['kueri_pencarian']))
    state["question"] = ques_arr
    return state

async def rag_search(state):
    for index, item in enumerate(state['question']) :
        query = state["question"][index].rag_ques

        search = DuckDuckGoSearchResults(output_format="list")
        results_list = search.invoke(state["question"][index].ques)

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
        for doc, _score in docs_pdf:
            bps_id = ""
            type = ""
            if 'pub_id' in doc.metadata : 
                bps_id = doc.metadata['pub_id']
                type = 'pub'
            if 'brs_id' in doc.metadata : 
                bps_id = doc.metadata['brs_id']
                type = 'brs'
            
            state["question"][index].rag_publikasi_brs.append(
                RagPublikasiBRS( 
                    id = str(uuid.uuid4()),
                    bps_id = bps_id,
                    type = type,
                    title = doc.metadata['title'], 
                    halaman= int(doc.id.split(':')[-2])+1, 
                    content = doc.page_content, 
                    rl_date = doc.metadata['rl_date'], 
                    score= _score
                )
            )

        docs_table = get_rag_data_table_arr(query, 5)
        for doc, _score in docs_table:
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

async def rag_validate(state):
    for index, item in enumerate(state['question']) :
        ques = state["question"][index].ques
        # print('ques')
        chunks = ""

        for item in state["question"][index].rag_publikasi_brs :
            chunks += item.print() +'\n\n'
        for item in state["question"][index].rag_data :
            chunks += item.print() +'\n\n'
        for item in state["question"][index].ddgs :
            chunks += item.print() +'\n\n'

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
        id_keep_rag = await llm_query(prompt, os.getenv('Whatsapp7600_03_Api_KEY'),config={
            "response_mime_type": "application/json",
            "response_json_schema":  {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
        })

        print(id_keep_rag)

        id_keep_rag = json.loads(id_keep_rag.replace("```",""))

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
       