from peewee import *
from db.db import BaseModel
from datetime import datetime, timedelta
from wablas.send import send_end_session

class User(BaseModel):
    nama = CharField(max_length=255)
    notelp = CharField(unique=True, max_length=15)
    email = CharField(unique=True, max_length=255, null=True)
    nama_lengkap = CharField(max_length=255, null=True)
    pekerjaan = CharField(max_length=255, null=True)
    instansi = CharField(max_length=255, null=True)
    tahun_lahir = IntegerField()
    created_at = DateTimeField(default=datetime.now)

class ChatSession(BaseModel):
    phone = CharField(max_length=15)
    layanan = SmallIntegerField(default=0) #0
    use_ai = BooleanField(default=False)
    is_done = BooleanField(default=False)
    need_human = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)


class ChatMessage(BaseModel):
    session = ForeignKeyField(ChatSession, backref="messages", null=True)
    role = CharField(max_length=10)   # user / bot / sis
    content = TextField()
    created_at = DateTimeField(default=datetime.now)


class Ticket(BaseModel):
    user = ForeignKeyField(User, field='notelp', backref='ticket')
    content = TextField()
    created_at = DateTimeField(default=datetime.now)


SESSION_TTL_HOURS = 24
def session_cutoff_time():
    return datetime.datetime.now() - datetime.timedelta(hours=SESSION_TTL_HOURS)

def get_or_create_active_session(phoneNumber: str):
    session = get_active_session(phoneNumber)

    if session:
        return session, False
    
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

def iddle_task_konsultasi():
    ten_minutes_ago = datetime.now() - timedelta(hours=12)
    idle_sessions = (
        ChatSession
        .select(
            ChatSession,
            fn.MAX(ChatMessage.created_at).alias("last_chat_time")
        )
        .where(
            (ChatSession.layanan == 1) &
            (ChatSession.is_done == False)
        )
        .join(ChatMessage)
        .group_by(ChatSession)
        .having(fn.MAX(ChatMessage.created_at) < ten_minutes_ago)
    )

    for item in idle_sessions :
        last_msg = (ChatMessage
            .select()
            .where(ChatMessage.session == item.id)
            .order_by(ChatMessage.created_at.desc())
            .first())
        
        if last_msg.role == 'user' :
            item.is_done = True
            item.save()


def iddle_task_ai():
    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
    idle_sessions = (
        ChatSession
        .select(
            ChatSession,
            fn.MAX(ChatMessage.created_at).alias("last_chat_time")
        )
        .where(
            (ChatSession.layanan == 3) &
            (ChatSession.is_done == False)
        )
        .join(ChatMessage)
        .group_by(ChatSession)
        .having(fn.MAX(ChatMessage.created_at) < ten_minutes_ago)
    )

    for item in idle_sessions :
        last_msg = (ChatMessage
            .select()
            .where(ChatMessage.session == item.id)
            .order_by(ChatMessage.created_at.desc())
            .first())
        
        if last_msg.role == 'user' :
            item.is_done = True
            item.save()

            send_end_session(item.phone)


def get_active_session(session_in_works):
    five_second_ago = datetime.now() - timedelta(seconds=5)
    batch_sessions = (
        ChatSession
        .select(
            ChatSession,
            fn.MAX(ChatMessage.created_at).alias("last_chat_time")
        )
        .where(
            ( (ChatSession.layanan == 2) | (ChatSession.layanan == 3) ) &
            (ChatSession.is_done == False) & (ChatSession.id.not_in(session_in_works))
        )
        .join(ChatMessage)
        .group_by(ChatSession)
        .having(fn.MAX(ChatMessage.created_at) < five_second_ago)
    )

    return batch_sessions[:(5 - len(session_in_works))]

def close_24_hour():
    twenty_four_hours_ago = datetime.now() - timedelta(hours=24)

    sessions_to_close = (
        ChatSession
        .select(ChatSession.id)
        .join(ChatMessage)
        .where(ChatSession.is_done == False)
        .group_by(ChatSession)
        .having(fn.MAX(ChatMessage.created_at) < twenty_four_hours_ago)
    )

    update_query = (
        ChatSession
        .update(is_done=True)
        .where(ChatSession.id.in_(sessions_to_close))
    )

    rows_updated = update_query.execute()

    print(f"Berhasil menutup {rows_updated} sesi chat yang idle selama 24 jam.")
