import mimetypes
import os
import base64
from dotenv import load_dotenv, find_dotenv
from _global import logger
import httpx, json

load_dotenv(find_dotenv())

TOKEN = os.getenv('WABLAS_TOKEN')
SECRET_KEY =  os.getenv('WABLAS_SECRET_KEY')

async def send_simple_text(phone: str, message:str) :
    flag = "instant"  # Optional: Enable extended message processing

    # Combine token and secret key exactly as in the PHP script
    combined_token = f"{TOKEN}.{SECRET_KEY}"

    # Set up the API endpoint and query parameters
    url = "https://tegal.wablas.com/api/send-message"
    params = {
        "token": combined_token,
        "phone": phone,
        "message": message,
        "flag": flag
    }

    while True:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                # (Opsional) return response jika berhasil
                break
                
            except httpx.HTTPError as e:
                # httpx.HTTPError menangkap semua error terkait request dan HTTP status
                logger.info(f"Request failed: {e}")
                return None

async def send_simple_image(phone: str, caption:str, file_path: str) :

    # Gather file metadata to simulate PHP's $_FILES array
    # Membaca file dan mengubahnya menjadi base64
    with open(file_path, "rb") as image_file:
        file_content = image_file.read()
        file_base64 = base64.b64encode(file_content).decode('utf-8')

    # Simulasi metadata $_FILES['upload_file'] dari PHP
    file_info = {
        "name": os.path.basename(file_path),
        "type": "image/jpeg", # Sesuaikan dengan mimetype file Anda
        "tmp_name": file_path,
        "error": 0,
        "size": os.path.getsize(file_path)
    }

    # Payload data (dikirim sebagai form-urlencoded)
    data = {
        'phone': phone,
        # Untuk bulk message gunakan koma: '081XXXXXX91,0850011xxx'
        'caption': caption, 
        'file': file_base64,
        'data': json.dumps(file_info)
    }

    headers = {
        "Authorization": f"{TOKEN}.{SECRET_KEY}"
    }

    url = "https://tegal.wablas.com/api/send-image-from-local"

    while True:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, data=data)
                response.raise_for_status()
                
                # (Opsional) return response jika berhasil
                break
                
            except httpx.HTTPError as e:
                # httpx.HTTPError menangkap semua error terkait request dan HTTP status
                logger.info(f"Request failed: {e}")


async def send_menu(phone: str, work_status, nama_lengkap) :
    url = "https://tegal.wablas.com/api/v2/send-list"

    if work_status : 
        payload = {
            "data": [
                {
                    "phone": phone,
                    "message": {
                        "title": "Menu Layanan",
                        "description": f"""Halo {nama_lengkap}👋
Selamat datang di layanan virtual *Marasa by BPS Sulbar*

Untuk membantu kebutuhan Anda, silakan pilih jenis layanan terlebih dahulu :""",
                        "buttonText": "Pilih layanan",
                        "lists": [
                            {
                                "title": "1️⃣ Konsultasi Statistik",
                                "description": "Layanan permintaan data atau konsultasi terkait data statistik BPS."
                            },
                            {
                                "title": "2️⃣ Pengaduan",
                                "description": "Sampaikan keluhan atau kendala terhadap BPS."
                            },
                            {
                                "title": "3️⃣ Chat AI Statistik 🤖",
                                "description": "Tanya jawab cepat seputar data statistik, publikasi, konsep indikator, dan panduan umum BPS."
                            },
                            # {
                            #     "title": "4️⃣ Lainnya",
                            #     "description": "Kebutuhan lain yang belum termasuk menu di atas."
                            # }
                        ],
                        "footer": "Silakan pilih 😊"
                    }
                }
            ]
        }
    else :
        payload = {
            "data": [
                {
                    "phone": phone,
                    "message": {
                        "title": "Menu Layanan",
                        "description": f"""Halo {nama_lengkap}👋
Selamat datang di layanan virtual *Marasa by BPS Sulbar*

Untuk membantu kebutuhan Anda, silakan pilih jenis layanan terlebih dahulu :""",
                        "buttonText": "Pilih layanan",
                        "lists": [
                            {
                                "title": "2️⃣ Pengaduan",
                                "description": "Sampaikan keluhan atau kendala terhadap BPS."
                            },
                            {
                                "title": "3️⃣ Chat AI Statistik 🤖",
                                "description": "Tanya jawab cepat seputar data statistik, publikasi, konsep indikator, dan panduan umum BPS."
                            },
                            # {
                            #     "title": "4️⃣ Lainnya",
                            #     "description": "Kebutuhan lain yang belum termasuk menu di atas."
                            # }
                        ],
                        "footer": "Silakan pilih 😊"
                    }
                }
            ]
        }

    headers = {
        "Authorization": f"{TOKEN}.{SECRET_KEY}",
        "Content-Type": "application/json"
    }

    while True:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                # (Opsional) return response jika berhasil
                break
                
            except httpx.HTTPError as e:
                # httpx.HTTPError menangkap semua error terkait request dan HTTP status
                logger.info(f"Request failed: {e}")

async def send_end_session(phone: str) :
    flag = "instant"  # Optional: Enable extended message processing

    # Combine token and secret key exactly as in the PHP script
    combined_token = f"{TOKEN}.{SECRET_KEY}"

    # Set up the API endpoint and query parameters
    url = "https://tegal.wablas.com/api/send-message"
    params = {
        "token": combined_token,
        "phone": phone,
        "message": "Terima kasih sudah menghubungi *Marasa by BPS Sulbar*. Jangan ragu hubungi kami lagi jika butuh bantuan lainnya. 😊",
        "flag": flag
    }

    while True:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                # (Opsional) return response jika berhasil
                break
                
            except httpx.HTTPError as e:
                # httpx.HTTPError menangkap semua error terkait request dan HTTP status
                logger.info(f"Request failed: {e}")