def end_checker(state):
    msg = state["message"].lower()
    end_words = ["terima kasih", "cukup", "selesai"]

    state["is_done"] = any(w in msg for w in end_words)
    return state