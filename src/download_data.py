import os
import requests
import pandas as pd
import argparse
from dotenv import load_dotenv, find_dotenv

# 1. LOAD ENV (Parent Folder)
load_dotenv(find_dotenv())
API_KEY = os.getenv("API_BPS")
DOMAIN = "7600"
BASE_URL = "https://webapi.bps.go.id/v1/api"

def get_categories():
    """Mengambil semua subjek (CSA) yang tersedia"""
    url = f"{BASE_URL}/list/model/subcatcsa/domain/{DOMAIN}/key/{API_KEY}/"
    print(url)

    while True: 
        response = requests.get(url).json()
        if response['status'] == 'OK':
            return response['data'][1]



def get_subjects(subcat):
    """Mengambil semua subjek (CSA) yang tersedia"""
    url = f"{BASE_URL}/list/model/subjectcsa/domain/{DOMAIN}/subcat/{subcat}/key/{API_KEY}/"
    print(url)
    while True: 
        response = requests.get(url).json()
        if response['status'] == 'OK':
            return response['data'][1]
        
def get_table(subject ):
    """Mengambil semua subjek (CSA) yang tersedia"""
    url = f"{BASE_URL}/list/model/tablestatistic/domain/{DOMAIN}/subject/{subject}/key/{API_KEY}/"
    print(url)
    while True: 
        response = requests.get(url).json()
        if response['status'] == 'OK':
            return response['data'][1]
        

def get_detail_table(id ):
    """Mengambil semua subjek (CSA) yang tersedia"""
    url = f"{BASE_URL}/view/model/tablestatistic/domain/{DOMAIN}/lang/ind/id/{id}/key/{API_KEY}/"
    print(url)
    while True: 
        response = requests.get(url).json()
        if response['status'] == 'OK':
            return response['data'][1]
        
def download_main_data():
    categories = get_categories()
    
    for cate in categories:
        subject_a = get_subjects(cate['subcat_id'])
        for subjec in subject_a:
            tables = get_table(subjec['sub_id'])
            for item in tables :
                abc = get_detail_table(item['id'])
                print(abc)
                break
            break
        break 
        
            
