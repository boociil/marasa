from langchain_openai import ChatOpenAI
from rag.retriever import get_retriever
from rag.prompts import STAT_PROMPT

llm = ChatOpenAI(model="gpt-4o-mini")
retriever = get_retriever()

def rewrite_query(state):
    history = "\n".join(state["chat_history"])
    prompt = f"Ubah menjadi pertanyaan mandiri:\n{history}\nQ:{state['message']}"
    state["message"] = llm.invoke(prompt).content
    return state

def rag_search(state):
    docs = retriever.invoke(state["message"])
    state["rag_context"] = "\n\n".join([d.page_content for d in docs])
    return state

def rag_answer(state):
    prompt = STAT_PROMPT.format(
        context=state["rag_context"],
        question=state["message"]
    )
    state["answer"] = llm.invoke(prompt).content
    return state