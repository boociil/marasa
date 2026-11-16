from db.models import User, ChatSession, ChatMessage, Ticket, Petugas, JadwalPetugas
from peewee_async import MySQLDatabase
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv()) 

def init_db(): 
    db = MySQLDatabase(
        os.getenv('DB_DATABASE'),
        user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT'))
    )

    db.connect()
    db.create_tables([Petugas, User, ChatSession, ChatMessage, Ticket, JadwalPetugas])
    print("DB ready")