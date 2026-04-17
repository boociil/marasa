from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

def route_intent(state):
    prompt = f"""
    Klasifikasikan pesan user ke salah satu layanan BPS:

    1. konsultasi_statistik
    2. pengaduan_layanan
    3. pengaduan_lainnya
    4. lainnya

    Message: {state["message"]}

    Return JSON:
    intent, service_type
    """

    result = llm.invoke(prompt).content

    # For starter → simple rules fallback
    msg = state["message"].lower()
    if "data" in msg or "statistik" in msg:
        state["service_type"] = "konsultasi_statistik"
    elif "layanan" in msg and "adu" in msg:
        state["service_type"] = "pengaduan_layanan"
    elif "adu" in msg:
        state["service_type"] = "pengaduan_lainnya"
    else:
        state["service_type"] = "lainnya"

    return state