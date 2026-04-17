def detect_followup(state):
    msg = state["message"].lower()
    keywords = ["lagi", "selain", "terus", "lanjut"]

    state["is_followup"] = any(k in msg for k in keywords)
    return state