import argparse
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM

from get_embedding_function import get_embedding_function

CHROMA_PATH = "../chroma"

PROMPT_TEMPLATE = """
Kamu adalah AI Statistical Research Assistant yang bekerja menggunakan Retrieval-Augmented Generation (RAG).

Tugas utama kamu adalah menjawab pertanyaan HANYA berdasarkan konteks dokumen yang diberikan oleh retriever. Jangan pernah menggunakan pengetahuan di luar konteks.

=====================
ATURAN UTAMA
=====================

1. Gunakan HANYA informasi dari CONTEXT.
2. Jika jawaban tidak ada di context → katakan:
   "Data tidak ditemukan dalam sumber yang tersedia."
3. Jangan pernah menebak angka.
4. Jangan menggabungkan beberapa angka menjadi kesimpulan baru kecuali jelas tertulis.
5. Jangan membuat sumber palsu.

=====================
PRIORITAS DATA
=====================

Jika terdapat beberapa data:
- Pilih data paling terbaru.
- Utamakan sumber resmi (BPS, World Bank, IMF, pemerintah, jurnal).
- Jika ada perbedaan angka → tampilkan keduanya + jelaskan singkat.

=====================
FORMAT JAWABAN (WAJIB)
=====================

Jawab secara ringkas dan berbasis fakta.

Struktur:

📊 Data Utama:
[angka + indikator]

📅 Tahun:
[tahun data]

📚 Sumber:
[nama dokumen / institusi jika tersedia di context]

📝 Catatan:
[opsional — misalnya yoy, harga konstan, provisional]

=====================
PENCEGAHAN HALLUCINATION
=====================

Jika context kosong atau tidak relevan:

Jawab:
"Saya tidak menemukan data yang relevan pada basis pengetahuan."

JANGAN:
- menggunakan knowledge model
- membuat estimasi
- memberikan opini

=====================
GAYA JAWABAN
=====================

- Profesional
- Langsung ke inti
- Tidak bertele-tele
- Tidak menjelaskan proses pencarian
- Tidak menyebut kata "context"

=====================
MODE ANALISIS (AKTIF HANYA JIKA DIMINTA)
=====================

Jika user meminta analisis atau tren:

Tambahkan maksimal 3 kalimat tentang:
- arah perubahan
- perbandingan
- insight singkat

Jangan melakukan spekulasi penyebab tanpa data.

Jawab pertanyaan berdasarkan konteks berikut:

{context}

---

Jawab pertanyaan berdasarkan konteks di atas: {question}

---

"""


def main():
    # Create CLI.
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text
    query_rag(query_text)


def query_rag(query_text: str):
    # Prepare the DB.
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # Search the DB.
    results = db.similarity_search_with_score(query_text, k=10)

    print(results)

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)
    # print(prompt)

    # model = OllamaLLM(model="gemma2:2b")
    model = OllamaLLM(model="qwen3:0.6b")
    response_text = model.invoke(prompt)

    sources = [doc.metadata.get("id", None) for doc, _score in results]
    formatted_response = f"Response: {response_text}\nSources: {sources}"
    print(formatted_response)
    return response_text


if __name__ == "__main__":
    main()
