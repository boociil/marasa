def check_registration(state):
    # TODO replace with real DB/API
    registered_users = ["user_1", "user_2"]

    state["is_registered"] = state["user_id"] in registered_users

    if not state["is_registered"]:
        state["answer"] = (
            "Untuk menggunakan Pelayanan Statistik Terpadu BPS, "
            "silakan daftar terlebih dahulu."
        )
    return state