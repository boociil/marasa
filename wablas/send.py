import requests
import mimetypes
import os
import base64
from dotenv import load_dotenv, find_dotenv
from loguru import logger

load_dotenv(find_dotenv())

TOKEN = os.getenv('WABLAS_TOKEN')
SECRET_KEY =  os.getenv('WABLAS_SECRET_KEY')

def send_simple_text(phone: str, message:str) :
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

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.info(f"Request failed: {e}")

def send_simple_image(phone: str, caption:str, file_path: str) :

    # Gather file metadata to simulate PHP's $_FILES array
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)

    # 1. Read and base64 encode the file
    with open(file_path, "rb") as image_file:
        file_content = image_file.read()
        # Decode to utf-8 string so it can be sent properly in the form payload
        encoded_file = base64.b64encode(file_content).decode('utf-8')


    # 3. Prepare the parameters
    params = {
        'phone': phone, # Untuk bulk message gunakan koma: '081XXXXXX91,0850011xxx'
        'caption': caption,       # Kosongkan atau gunakan None jika tidak ada caption
        'file': encoded_file,
        'data': {
            "name": filename,
            "type": mime_type or "application/octet-stream",
            "tmp_name": file_path, 
            "error": 0,
            "size": file_size
        }
    }

    # 4. HTTP Headers
    headers = {
        "Authorization": f"{TOKEN}.{SECRET_KEY}"
    }

    url = "https://tegal.wablas.com/api/send-image-from-local"

    try:
        # 5. Execute the POST request
        # verify=False is equivalent to CURLOPT_SSL_VERIFYHOST and VERIFYPEER = 0
        response = requests.post(url, headers=headers, data=params)
        response.raise_for_status()

    except FileNotFoundError:
        logger.info(f"Error: The file at {file_path} was not found.")
    except requests.exceptions.RequestException as e:
        logger.info(f"Request failed: {e}")