import re
from typing import Dict

PII_PATTERNS = [
    r"\b\d{16}\b",            # NIK
    r"\b\d{15}\b",            # NPWP lama
    r"\b08\d{8,11}\b",        # nomor HP
    r"alamat lengkap",
    r"nama lengkap responden",
]
SENSITIVE_KEYWORDS = [
    "microdata",
    "data mentah",
    "data individu",
    "raw data",
    "database bps",
    "data perusahaan",
]

TOXIC_WORDS = [
    "bodoh", "tolol", "anjing", "bangsat"
]

OUT_SCOPE = [
    "cuaca", "resep masakan", "ramalan zodiak"
]

def safety_guardrail(state: Dict):
    text = state["user_input"].lower()

    flags = {
        "pii_detected": False,
        "sensitive_data_request": False,
        "toxic_language": False,
        "out_of_scope": False,
        "need_human": False,
        "blocked": False,
        "reason": ""
    }

    # --- Detect PII ---
    for pattern in PII_PATTERNS:
        if re.search(pattern, text):
            flags["pii_detected"] = True
            flags["blocked"] = True
            flags["reason"] = "Permintaan mengandung data pribadi"
            break

    # --- Sensitive data ---
    if any(k in text for k in SENSITIVE_KEYWORDS):
        flags["sensitive_data_request"] = True
        flags["need_human"] = True
        flags["reason"] = "Permintaan data sensitif/microdata"

    # --- Toxic language ---
    if any(word in text for word in TOXIC_WORDS):
        flags["toxic_language"] = True
        flags["need_human"] = True
        flags["reason"] = "Bahasa tidak pantas"

    # --- Out of scope ---
    if any(word in text for word in OUT_SCOPE):
        flags["out_of_scope"] = True

    state["safety_flags"] = flags
    return state