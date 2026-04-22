import os
from dotenv import load_dotenv, find_dotenv
import os
import json
import unicodedata
from pdf2image import convert_from_path

load_dotenv(find_dotenv()) 
PDF_JSON = os.getenv('PDF_JSON')
PATH_LAST = os.getenv('PATH_LAST')

def populate_image():
    PATH_LAST = ""
    MULAI_ENBED = True

    if os.path.exists(os.getenv('PATH_LAST')):
        try:
            with open(os.getenv('PATH_LAST'), 'r') as f:
                PATH_LAST = str(f.read().strip())
                MULAI_ENBED = True
        except FileNotFoundError:
            nomor_baris = 0
    else : 
        MULAI_ENBED = False
        return
    

    data = {}
    with open(PDF_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data['publication'] :
        title = secure_filename(item['rl_date']+'-'+item['title'])
        path = os.path.join(os.getenv("PDF_ALL_FOLDER_Publikasi"), title.replace("/", "-") + ".pdf")
        path_folder = os.path.join(os.getenv("IMAGES_FOLDER_Publikasi"), title.replace("/", "-"))
        print(title)
        print()

        if not os.path.exists(path):
            continue

        if os.path.exists(path_folder):
            continue

        if MULAI_ENBED :
            os.makedirs(path_folder, exist_ok=True)
            pages = convert_from_path(path, 200)

            i = 1
            for page in pages:
                page.save(os.path.join(path_folder,str(i)+'.jpg'), 'JPEG')
                i = i+1

            if path == PATH_LAST :
                MULAI_ENBED = False
                break

    for item in data['pressrelease'] :
        title = secure_filename(item['rl_date']+'-'+str(item['brs_id'])+'-'+str(item['subj']))
        path = os.path.join(os.getenv("PDF_ALL_FOLDER_BRS"), title.replace("/", "-") + ".pdf")
        path_folder = os.path.join(os.getenv("IMAGES_FOLDER_BRS"), title.replace("/", "-"))
        print(title)
        print()

        if not os.path.exists(path):
            continue

        if os.path.exists(path_folder):
            continue

        if MULAI_ENBED :
            os.makedirs(path_folder, exist_ok=True)
            pages = convert_from_path(path, 200)

            i = 1
            for page in pages:
                page.save(os.path.join(path_folder,str(i)+'.jpg'), 'JPEG')
                i = i+1

            if path == PATH_LAST :
                MULAI_ENBED = False
                break


INVALID_FILE_CHARS = '/\\?%*:|"<>' # https://en.wikipedia.org/wiki/Filename#Reserved_characters_and_words

def secure_filename(filename):
    # keep only valid ascii chars
    output = list(unicodedata.normalize("NFKD", filename))

    # special case characters that don't get stripped by the above technique
    for pos, char in enumerate(output):
        if char == '\u0141':
            output[pos] = 'L'
        elif char == '\u0142':
            output[pos] = 'l'

    # remove unallowed characters
    output = [c if c not in INVALID_FILE_CHARS else '_' for c in output]
    return "".join(output).encode("ASCII", "ignore").decode()