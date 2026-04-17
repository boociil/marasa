from peewee import *
from src.graph.db.db import BaseModel
import datetime

class User(BaseModel):
    nama = CharField(max_length=255)
    notelp = CharField(unique=True, max_length=15)
    email = CharField(unique=True, max_length=255)
    nama_lengkap = CharField(max_length=255)
    pekerjaan = CharField(max_length=255)
    instansi = CharField(max_length=255)
    created_at = DateTimeField(default=datetime.datetime.now)

class ChatSession(BaseModel):
    user_id = CharField()
    session_id = CharField(unique=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)


class ChatMessage(BaseModel):
    session = ForeignKeyField(ChatSession, backref="messages")
    role = CharField()   # user / bot
    content = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)
