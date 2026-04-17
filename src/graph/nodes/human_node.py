FRUSTRATION_WORDS = [
    "tidak membantu",
    "tidak jelas",
    "bingung",
    "kok tidak bisa",
    "jelek",
    "lama",
    "kesal",
    "marah",
]

HUMAN_KEYWORDS = [
    "petugas",
    "admin",
    "operator",
    "cs",
    "customer service",
    "manusia",
    "orang bps",
    "hubungkan saya",
]

def detect_frustration(text: str) -> bool:
    text = text.lower()
    return any(k in text for k in FRUSTRATION_WORDS)

def detect_human_request(text: str) -> bool:
    text = text.lower()
    return any(k in text for k in HUMAN_KEYWORDS)


def human_node(state):
    text = state['new_chat'][-1]

    if detect_human_request(text):
        state['need_human'] = True
        return state

    if detect_frustration(text):
        state['need_human'] = True
        return state

    if len(state['chat_history']) + len(state['new_chat']) == 15:
        state['need_human'] = True
        return state

    return state