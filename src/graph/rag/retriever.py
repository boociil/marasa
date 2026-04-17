from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain_openai import ChatOpenAI
from .chroma_client import get_vectorstore

def get_retriever():
    db = get_vectorstore()

    # results = db.similarity_search_with_score(query_text, k=10)


    base = db.as_retriever(
        search_type="mmr",
        search_kwargs={"k":6, "fetch_k":20}
    )

    llm = ChatOpenAI(model="gpt-4o-mini")
    compressor = LLMChainExtractor.from_llm(llm)

    return ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base
    )