from loguru import logger

logger.add(
    "log/api_{time:YYYY-MM-DD}.log", # Nama file akan jadi seperti log/api_2026-05-26.log
    rotation="00:00",                # Buat file baru setiap jam 12 malam (tengah malam)
    retention="30 days",             # Opsional: Otomatis hapus file log yang lebih tua dari 30 hari
    level="INFO"
)
