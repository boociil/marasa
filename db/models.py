from peewee import CharField, IntegerField, DateTimeField, SmallIntegerField, BooleanField, ForeignKeyField, TextField, fn
from db.db import BaseModel
from datetime import datetime, timedelta, date
from wablas.send import send_end_session
from _global import logger

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


async def get_or_create_active_session(phoneNumber: str):
    session = await get_active_session(phoneNumber)

    if session:
        return session, False
    
    # buat session baru
    new_session = await ChatSession.aio_create(phone = phoneNumber)
    return new_session, True


async def get_active_session(phoneNumber: str) -> ChatSession | None:
    SESSION_TTL_HOURS = 24
    session_cutoff_time = datetime.now() - timedelta(hours=SESSION_TTL_HOURS)
   
    try:
        session = await ChatSession.aio_get(
                (ChatSession.phone == phoneNumber) &
                (ChatSession.is_done == False) &
                (ChatSession.created_at >= session_cutoff_time)
            )
        return session

    except ChatSession.DoesNotExist:
        return None

async def get_user_by_phone(phoneNumber: str) -> User | None:
    try:
        user = await User.aio_get(User.notelp == phoneNumber)
        return user

    except User.DoesNotExist:
        return None
    

async def load_last_messages(session: ChatSession):
    query = await ChatMessage.select().where(ChatMessage.session == session).order_by(ChatMessage.created_at.desc()).aio_execute()
    messages = list(query)
    messages.reverse()

    content = []

    for item in messages: 
        if item.role == 'user' and item.content != '':
            content.append('user : '+item.content)
        elif item.role == 'bot' and item.content != '':
            content.append('bot : '+item.content)

    return content


async def iddle_task_konsultasi():
    one_hour_ago = datetime.now() - timedelta(hours=1)
    hari_ini_awal = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    idle_sessions = list(await ChatSession
        .select(
            ChatSession,
            fn.MAX(ChatMessage.created_at).alias("last_chat_time")
        )
        .where(
            (ChatSession.layanan == 1) &
            (ChatSession.is_done == False) & 
            (ChatSession.created_at < hari_ini_awal)
        )
        .join(ChatMessage)
        .group_by(ChatSession)
        .having(fn.MAX(ChatMessage.created_at) < one_hour_ago)
        .aio_execute()
    )

    for item in idle_sessions:
        item.is_done = True
        await item.aio_save()


async def iddle_task_ai(session_in_works_id):
    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
    idle_sessions = list(await ChatSession
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
        .aio_execute()
    )

    for item in idle_sessions:
        if item.id in session_in_works_id:
            continue
        last_msg = list(await ChatMessage.select().where(ChatMessage.session == item.id).order_by(ChatMessage.created_at.desc()).aio_execute())
        
        if last_msg and last_msg[0].role == 'bot':
            item.is_done = True
            await item.aio_save()
            await send_end_session(item.phone)


async def get_active_session_not_arr(session_in_works_id):
    five_second_ago = datetime.now() - timedelta(seconds=5)

    last_msg_subquery = (ChatMessage
                     .select(fn.MAX(ChatMessage.id))
                     .group_by(ChatMessage.session))

    # PERBAIKAN: Pisahkan kondisi base dan tambahan untuk menghindari error jika session_in_works_id kosong
    conditions = (
        ( (ChatSession.layanan == 2) | (ChatSession.layanan == 3) ) &
        (ChatSession.is_done == False) &
        (ChatMessage.id << last_msg_subquery) & # Pastikan ini pesan terakhir
        (ChatMessage.role == 'user') &          # Role terakhir adalah user
        (ChatMessage.created_at < five_second_ago) # Sudah lewat 5 detik
    )
    
    if session_in_works_id:
        conditions = conditions & (ChatSession.id.not_in(session_in_works_id))

    batch_sessions = list(await (ChatSession
            .select(ChatSession, ChatMessage)
            .join(ChatMessage)
            .where(conditions)
        )
        .aio_execute()
    )

    return batch_sessions


async def close_24_hour():
    twenty_four_hours_ago = datetime.now() - timedelta(hours=24)

    sessions_to_close = list(await ChatSession
        .select(ChatSession.id)
        .join(ChatMessage)
        .where(ChatSession.is_done == False)
        .group_by(ChatSession)
        .having(fn.MAX(ChatMessage.created_at) < twenty_four_hours_ago)
        .aio_execute()
    )

    if sessions_to_close:
        ids_to_close = [s.id for s in sessions_to_close]
        rows_updated = await ChatSession.update(is_done=True).where(ChatSession.id.in_(ids_to_close)).aio_execute()
        print(f"Berhasil menutup {rows_updated} sesi chat yang idle selama 24 jam.")
    else:
        print("Tidak ada sesi chat idle 24 jam yang perlu ditutup.")