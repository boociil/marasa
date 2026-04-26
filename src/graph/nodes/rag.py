from src.graph.rag.retriever import get_rag_data, get_rag_data_table
from src.graph.text import LLM_PROMPT
from src.graph.llm import llm_query
from src.graph.state import QuestionModel, RagPublikasiBRS, RagData, AnswerModel
from dotenv import load_dotenv, find_dotenv
import os
import uuid
import json
import unicodedata
from google.genai.types import Tool, GenerateContentConfig

load_dotenv(find_dotenv()) 

ai_disclaimen = "*AI dapat membuat kesalahan"

def pecah_question(state) :
      # print("rag_rewrite_query")
    history = "\n".join(item for item in state["chat_history"] if item.startswith("user"))

    new_chat = "\n".join(state["new_chat"])

    prompt = f"""
Anda adalah alat ekstraktor pertanyaan.

Tujuan:
Ekstrak semua pertanyaan dari teks dan kembalikan dalam bentuk array JSON yang rapi.

Aturan ketat:
- Pertanyaan bisa tampa tanda ? / tanya
- Tanpa penjelasan.
- Tidak boleh ada teks tambahan.
- Pertahankan bahasa asli.
- Hapus duplikat.
- Jika tidak ada pertanyaan, kembalikan: []
- perhatikan Riwayat percakapan namun kalo tidak relevan hilangkan

Riwayat percakapan:
{history if history.strip() != "" else "-"}

Teks yang akan dianalisis:
{new_chat}
"""

    pecah_question_hasil = llm_query(prompt, os.getenv('Whatsapp7600_01_Api_KEY'),config={
        "response_mime_type": "application/json",
        "response_json_schema":  {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
    })

    ques_arr = []
    for item in json.loads(pecah_question_hasil ):
        ques_arr.append(QuestionModel(ques=item))
    state["question"] = ques_arr

    return state

def transform_untuk_rag(state) :
    question_str_arr = []
    for item in state["question"] :
        question_str_arr.append(item.ques)

    prompt = f"""
Anda adalah pengoptimal kueri pencarian untuk pengambilan data RAG.

Ubah setiap pertanyaan menjadi kueri pencarian terperinci yang akan mengambil dokumen-dokumen paling relevan.

Aturan:
- Pertahankan bahasa asli
- Perluas konteks dan kata kunci
- Buat agar mandiri
- Hapus kata-kata percakapan
- JANGAN menjawab pertanyaan
- Jumlah hasil harus sama dengan jumlah pertanyaan
- Jangan memperbanyak pertanyaan

Contoh:
Pertanyaan: “Apa roadmap AI?”
Kueri: “roadmap belajar kecerdasan buatan untuk pemula, keterampilan machine learning, Python, matematika, langkah demi langkah”

Beberapa Pertanyaan:
{question_str_arr}
"""
    extract_rag = llm_query(prompt, os.getenv('Whatsapp7600_02_Api_KEY'),config={
        "response_mime_type": "application/json",
        "response_json_schema":  {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
    })

    extract_rag = json.loads(extract_rag)
    for index, item in enumerate(extract_rag):         
        state["question"][index].rag_ques = extract_rag[index]
    return state


def rag_search(state):
    for index, item in enumerate(state['question']) :
        query = state["question"][index].rag_ques

        docs_pdf = get_rag_data(query)
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

        docs_table = get_rag_data_table(query)
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

def rag_validate(state):
    for index, item in enumerate(state['question']) :
        ques = state["question"][index].ques
        print('ques')
        chunks = ""

        for item in state["question"][index].rag_publikasi_brs :
            chunks += item.print() +'\n\n'
        for item in state["question"][index].rag_data :
            chunks += item.print() +'\n\n'

        prompt =f""""
Kamu adalah penilai relevansi dokumen untuk sistem RAG.

Tugas:
Pilih HANYA potongan pengetahuan (knowledge chunks) yang benar-benar membantu menjawab pertanyaan.

Aturan ketat:
- Pilih chunk yang berisi fakta yang bisa langsung dipakai untuk menjawab pertanyaan.
- Hapus chunk yang hanya sedikit berkaitan.
- Hapus chunk yang tidak membantu menjawab pertanyaan.
- Jika tidak ada yang relevan, kembalikan list kosong.
- JANGAN menjawab pertanyaan.
- Output HARUS JSON saja, tanpa penjelasan.
- OUTPUT CUKUP Array dari id pengetahuan
- Urutkan dari yang paling relevan

Pertanyaan:
{ques}

Daftar knowledge chunks:
{chunks}"""
        
        print(prompt)
        id_keep_rag = llm_query(prompt, os.getenv('Whatsapp7600_03_Api_KEY'),config={
            "response_mime_type": "application/json",
            "response_json_schema":  {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
        })

        id_keep_rag = json.loads(id_keep_rag)

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
       
    return state

def rag_answer(state):
    for index, item in enumerate(state['question']) :
        ques = state["question"][index].ques
        chunks = ""

        for item in state["question"][index].rag_publikasi_brs_output :
            chunks += item.print() +'\n\n'
        for item in state["question"][index].rag_data_output :
            chunks += item.print() +'\n\n'

        if len(state["question"][index].rag_publikasi_brs_output) + len(state["question"][index].rag_data_output) == 0:
            state["question"][index].answer.append(AnswerModel(type="text", text="Maaf, kami belum menemukan data yang sesuai."))
            continue
        
        

        if len(state["question"][index].rag_publikasi_brs_output) > 0 :
            for i, item in enumerate(state["question"][index].rag_publikasi_brs_output) :
                state["question"][index].answer.append(AnswerModel(type="file", file_path= findImagePathPublikasiBRS(item)))


        prompt = LLM_PROMPT.format(
            context=chunks,
            question=ques
        )
        hasil = llm_query(prompt,  os.getenv('Whatsapp7600_04_Api_KEY'), config=GenerateContentConfig(
            tools=[
                {"url_context": {}},
            ],
        ))
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
       