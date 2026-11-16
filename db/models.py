from peewee import CharField, IntegerField, DateTimeField, SmallIntegerField, BooleanField, ForeignKeyField, TextField, TimeField, fn
from db.db import BaseModel
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from wablas.send import send_end_session
from _global import logger

# Zona waktu operasional PST.
WITA = ZoneInfo("Asia/Makassar")

# Mode sesi untuk fitur handoff petugas PST (khusus layanan 1).
MODE_MENUNGGU = 0   # menunggu petugas mengambil sesi
MODE_LIVE = 1       # live chat dua arah dengan petugas
MODE_MANUAL = 2     # petugas membalas dari perangkat sendiri
MODE_SELESAI = 3    # sesi ditutup


class Petugas(BaseModel):
    nama = CharField(max_length=255)
    notelp = CharField(unique=True, max_length=15)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)


class JadwalPetugas(BaseModel):
    """Jadwal petugas PST per hari dan sesi (zona WITA).

    Satu baris = satu petugas pada satu hari dan satu sesi.
    """

    petugas = ForeignKeyField(
        Petugas,
        field="id",
        backref="jadwal",
        on_delete="CASCADE",
    )
    hari = SmallIntegerField()          # ISO: 1=Senin ... 7=Minggu
    sesi = CharField(max_length=5)      # 'pagi' | 'siang'
    jam_mulai = TimeField()
    jam_selesai = TimeField()

    class Meta:
        table_name = "jadwal_petugas"
        indexes = (
            # Satu petugas hanya boleh punya satu baris per hari+sesi.
            (("petugas", "hari", "sesi"), True),
            # Mempercepat pencarian petugas yang bertugas pada jam tertentu.
            (("hari", "jam_mulai", "jam_selesai"), False),
        )


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
    handler = ForeignKeyField(Petugas, field="id", null=True, backref="sessions", on_delete="SET NULL")
    mode = SmallIntegerField(default=MODE_MENUNGGU)
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
                (
                    (ChatSession.created_at >= session_cutoff_time) |
                    (ChatSession.mode.in_([MODE_LIVE, MODE_MANUAL]))
                )
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


###########################################################################
# HANDOFF PETUGAS
###########################################################################

async def get_petugas_by_phone(phoneNumber: str) -> Petugas | None:
    try:
        return await Petugas.aio_get(Petugas.notelp == phoneNumber)
    except Petugas.DoesNotExist:
        return None


async def get_petugas_by_id(petugas_id: int) -> Petugas | None:
    try:
        return await Petugas.aio_get(Petugas.id == petugas_id)
    except Petugas.DoesNotExist:
        return None


async def get_active_petugas():
    return list(
        await Petugas
        .select()
        .where(Petugas.is_active == True)
        .order_by(Petugas.id)
        .aio_execute()
    )


async def get_petugas_bertugas(now: datetime | None = None):
    """Petugas aktif yang punya jadwal pada waktu tertentu (WITA).

    Batas jam mengikuti jadwal: `jam_mulai <= waktu < jam_selesai`.
    Dengan demikian pukul 12:00:00 masuk sesi siang, bukan pagi.
    `now` yang naive dianggap sudah dalam zona WITA.
    """
    if now is None:
        now_wita = datetime.now(WITA)
    elif now.tzinfo is None:
        now_wita = now.replace(tzinfo=WITA)
    else:
        now_wita = now.astimezone(WITA)

    hari = now_wita.isoweekday()
    waktu = now_wita.time().replace(microsecond=0)

    rows = await (
        Petugas
        .select(Petugas)
        .join(JadwalPetugas)
        .where(
            (Petugas.is_active == True) &
            (JadwalPetugas.hari == hari) &
            (JadwalPetugas.jam_mulai <= waktu) &
            (JadwalPetugas.jam_selesai > waktu)
        )
        .distinct()
        .order_by(Petugas.id)
        .aio_execute()
    )
    return list(rows)


async def get_session_by_id(session_id: int) -> ChatSession | None:
    rows = list(
        await ChatSession
        .select()
        .where(ChatSession.id == session_id)
        .limit(1)
        .aio_execute()
    )
    return rows[0] if rows else None


async def get_handoff_session(phoneNumber: str) -> ChatSession | None:
    """Sesi layanan 1 yang masih aktif, tanpa batas TTL 24 jam."""
    rows = list(
        await ChatSession
        .select()
        .where(
            (ChatSession.phone == phoneNumber) &
            (ChatSession.layanan == 1) &
            (ChatSession.is_done == False) &
            (ChatSession.mode.in_([MODE_MENUNGGU, MODE_LIVE, MODE_MANUAL]))
        )
        .order_by(ChatSession.id.desc())
        .limit(1)
        .aio_execute()
    )
    return rows[0] if rows else None


async def get_live_session_by_handler(petugas_id: int) -> ChatSession | None:
    rows = list(
        await ChatSession
        .select()
        .where(
            (ChatSession.handler == petugas_id) &
            (ChatSession.mode == MODE_LIVE) &
            (ChatSession.is_done == False)
        )
        .order_by(ChatSession.id.desc())
        .limit(1)
        .aio_execute()
    )
    return rows[0] if rows else None


async def claim_session(session_id: int, petugas_id: int, mode: int) -> bool:
    """Ambil sesi secara atomik. False berarti sudah diambil petugas lain."""
    updated = await (
        ChatSession
        .update(handler=petugas_id, mode=mode, updated_at=datetime.now())
        .where(
            (ChatSession.id == session_id) &
            (ChatSession.handler.is_null()) &
            (ChatSession.is_done == False)
        )
        .aio_execute()
    )
    return updated == 1

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
            (ChatSession.mode == MODE_MENUNGGU) &
            (ChatSession.created_at < hari_ini_awal)
        )
        .join(ChatMessage)
        .group_by(ChatSession)
        .having(fn.MAX(ChatMessage.created_at) < one_hour_ago)
        .aio_execute()
    )

    for item in idle_sessions:
        item.is_done = True
        item.mode = MODE_SELESAI
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
        .where(
            (ChatSession.is_done == False) &
            (ChatSession.mode.not_in([MODE_LIVE, MODE_MANUAL]))
        )
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