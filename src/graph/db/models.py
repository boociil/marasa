from peewee import *
from src.graph.db.db import BaseModel
import datetime

class User(BaseModel):
    nama = CharField(max_length=255)
    jid = CharField(unique=True, max_length=100)
    notelp = CharField(unique=True, max_length=15)
    email = CharField(unique=True, max_length=255, null=True)
    nama_lengkap = CharField(max_length=255, null=True)
    pekerjaan = CharField(max_length=255, null=True)
    instansi = CharField(max_length=255, null=True)
    tahun_lahir = IntegerField()
    created_at = DateTimeField(default=datetime.datetime.now)

class ChatSession(BaseModel):
    phone = CharField(max_length=15)
    user = ForeignKeyField(
        User,
        field='notelp',
        backref='sessions',
        null=True   # 🔥 ini kuncinya
    )
    layanan = SmallIntegerField(default=0) #0
    use_ai = BooleanField(default=False)
    is_done = BooleanField(default=False)
    need_human = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)


class ChatMessage(BaseModel):
    session = ForeignKeyField(ChatSession, backref="messages")
    role = CharField(max_length=10)   # user / bot / sis
    content = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)


class Ticket(BaseModel):
    user = ForeignKeyField(User, field='notelp', backref='ticket')
    content = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)


SESSION_TTL_HOURS = 24
def session_cutoff_time():
    return datetime.datetime.now() - datetime.timedelta(hours=SESSION_TTL_HOURS)

def get_or_create_active_session(phoneNumber: str):
    session = get_active_session(phoneNumber)

    if session:
        return session, False

    (
        ChatSession
        .update(is_done=True)
        .where(
            (ChatSession.user == phoneNumber) &
            (ChatSession.is_done == False)
        )
        .execute()
    )

    # buat session baru
    new_session = ChatSession.create(phone = phoneNumber)
    return new_session, True

def get_active_session(phoneNumber: str) -> dict | None:
    try:
        session = (
            ChatSession
            .select()
            .where(
                (ChatSession.phone == phoneNumber) &
                (ChatSession.is_done == False) &
                (ChatSession.created_at >= session_cutoff_time())
            )
            .order_by(ChatSession.created_at.desc())
            .get()
        )
        return session

    except ChatSession.DoesNotExist:
        return None

def get_user_by_phone(phoneNumber: str) -> dict | None:
    try:
        user = (
            User
            .select()
            .where(
                User.notelp == phoneNumber
            )
            .first()
        )
        return user

    except ChatSession.DoesNotExist:
        return None
    

def load_last_messages(session: ChatSession):
    query = (
        ChatMessage
        .select()
        .where(ChatMessage.session == session)
        .order_by(ChatMessage.created_at.desc())
    )

    # karena desc, kita balik lagi biar urutan normal
    messages = list(query)
    messages.reverse()

    content = []

    for item in messages: 
        if item.role == 'user' and item.content != '':
            content.append('user : '+item.content)
        elif item.role == 'bot' and item.content != '':
            content.append('bot : '+item.content)

    return content
