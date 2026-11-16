"""Alur handoff layanan Konsultasi Statistik (layanan = 1) ke petugas PST.

Isi modul ini:
- notifikasi satu kali ke pengguna bahwa pesan akan diteruskan ke petugas
- notifikasi list ke semua petugas aktif (satu list per sesi)
- penanganan pilihan petugas: Live Chat, Manual, Akhiri Sesi
- penerusan pesan dua arah saat mode live
- penutupan sesi handoff yang idle

Pipeline AI/RAG (graph/*) tidak disentuh oleh modul ini.
"""

import asyncio
import os
import re
from datetime import datetime, timedelta

from peewee import fn

from _global import logger
from db.models import (
    ChatSession,
    ChatMessage,
    MODE_LIVE,
    MODE_MANUAL,
    MODE_SELESAI,
    claim_session,
    get_active_petugas,
    get_live_session_by_handler,
    get_petugas_bertugas,
    get_petugas_by_id,
    get_session_by_id,
    get_user_by_phone,
)
from wablas.send import send_list_message, send_simple_text


###########################################################################
# TEKS
###########################################################################

USER_HANDOFF_TEXT = "Baik, pesan akan kami teruskan ke petugas kami agar segera direspon"

LIVE_ON_TEXT = "Live chat : ON\nPengguna: {nama} ({phone})"
LIVE_OFF_TEXT = "Live chat : OFF\nPengguna: {nama} ({phone})"

MANUAL_ON_TEXT = (
    "Mode manual : ON\n"
    "Pengguna: {nama} ({phone})\n"
    "Silakan balas langsung dari perangkat WhatsApp Anda."
)

TANPA_LIVE_TEXT = (
    "Tidak ada sesi live chat aktif. "
    "Silakan pilih 'Respon Live Chat' dari list konsultasi terlebih dahulu."
)

MARKER_NOTIF = "handoff_notif:{session_id}"

# Batas idle sesi live/manual sebelum ditutup otomatis.
HANDOFF_IDLE_HOURS = int(os.getenv("HANDOFF_IDLE_HOURS", "24"))


###########################################################################
# UTIL
###########################################################################

def nama_pengguna(user, fallback_phone: str = "") -> str:
    if user is not None:
        if user.nama_lengkap:
            return user.nama_lengkap
        if user.nama:
            return user.nama
    return fallback_phone or "-"


def is_text_message(data) -> bool:
    if data.file or data.url:
        return False

    tipe = (data.messageType or "").strip().lower()
    if tipe and tipe != "text":
        return False

    return bool(data.message and data.message.strip())


def survey_text() -> str:
    url = (os.getenv("SURVEY_URL") or "").strip()

    if not url:
        logger.warning("SURVEY_URL belum diisi di .env")
        return "Terima kasih telah menggunakan layanan kami."

    return (
        "Terima kasih telah menggunakan layanan kami.\n"
        f"Mohon bantu kami dengan mengisi survei kebutuhan data berikut: {url}"
    )


_PILIHAN_RE = re.compile(r"<~\s*([123])\b")
_PILIHAN_FALLBACK_RE = re.compile(r"^\s*([123])[\.\)]\s")
_SESI_RE = re.compile(r"#\s*(\d+)")


def parse_petugas_action(text: str):
    """Ambil (pilihan, session_id) dari balasan list Wablas.

    Wablas mengirim balik teks pilihan dengan awalan "<~ " (pola yang sama
    dipakai set_layanan.py). Session ID sengaja ditaruh di judul DAN deskripsi
    pilihan, lalu dicari dengan regex agar tetap terbaca apa pun yang dikirim.
    """
    clean = text.encode("ascii", "ignore").decode("utf-8").strip()

    sesi = _SESI_RE.search(clean)
    if sesi is None:
        return None, None

    pilihan = _PILIHAN_RE.search(clean)
    if pilihan is None:
        pilihan = _PILIHAN_FALLBACK_RE.search(clean)
    if pilihan is None:
        return None, None

    return int(pilihan.group(1)), int(sesi.group(1))


###########################################################################
# NOTIFIKASI
###########################################################################

async def notify_user_handoff_once(session: ChatSession, user) -> bool:
    """Kirim pemberitahuan ke pengguna, maksimal sekali per sesi."""
    if session is None or user is None:
        return False

    sudah = list(
        await ChatMessage
        .select()
        .where(
            (ChatMessage.session == session) &
            (ChatMessage.role == "bot") &
            (ChatMessage.content == USER_HANDOFF_TEXT)
        )
        .limit(1)
        .aio_execute()
    )
    if sudah:
        return False

    await send_simple_text(user.notelp, USER_HANDOFF_TEXT)
    await ChatMessage.aio_create(
        session=session,
        role="bot",
        content=USER_HANDOFF_TEXT,
    )
    return True


async def notify_petugas_new_session(session: ChatSession, user) -> bool:
    """Kirim SATU list per sesi ke petugas yang bertugas saat ini.

    Fallback: jika tidak ada petugas yang masuk jadwal, kirim ke semua
    petugas aktif agar konsultasi tidak menggantung.
    """
    if session is None:
        return False

    marker = MARKER_NOTIF.format(session_id=session.id)
    sudah = list(
        await ChatMessage
        .select()
        .where(
            (ChatMessage.session == session) &
            (ChatMessage.role == "sis") &
            (ChatMessage.content == marker)
        )
        .limit(1)
        .aio_execute()
    )
    if sudah:
        return False

    daftar_petugas = await get_petugas_bertugas()
    if not daftar_petugas:
        logger.warning(
            f"Tidak ada petugas yang masuk jadwal untuk sesi konsultasi "
            f"{session.id}; fallback ke semua petugas aktif"
        )
        daftar_petugas = await get_active_petugas()

    if not daftar_petugas:
        logger.warning(
            f"Tidak ada petugas aktif untuk sesi konsultasi {session.id}"
        )
        return False

    nama = nama_pengguna(user, session.phone)

    # Judul tiap pilihan memuat ID sesi karena Wablas mengirim balik judul
    # pilihan, bukan deskripsi. Deskripsi tetap memuat ID sebagai cadangan.
    rows = [
        {
            "title": f"1. Live Chat #{session.id}",
            "description": f"Teruskan pesan dua arah (sesi #{session.id})",
        },
        {
            "title": f"2. Manual #{session.id}",
            "description": f"Balas dari perangkat sendiri (sesi #{session.id})",
        },
        {
            "title": f"3. Akhiri #{session.id}",
            "description": f"Tutup sesi #{session.id}",
        },
    ]

    jumlah_terkirim = 0
    for petugas in daftar_petugas:
        terkirim = await send_list_message(
            phone=petugas.notelp,
            title="Konsultasi Baru",
            description=(
                f"Pengguna: {nama}\n"
                f"Nomor: {session.phone}\n"
                f"Sesi: #{session.id}"
            ),
            button_text="Pilih aksi",
            rows=rows,
            footer="Marasa by BPS Sulbar",
        )
        if terkirim:
            jumlah_terkirim += 1

    if jumlah_terkirim == 0:
        logger.warning(
            f"Gagal mengirim notifikasi konsultasi sesi {session.id} "
            f"ke seluruh petugas"
        )
        return False

    await ChatMessage.aio_create(
        session=session,
        role="sis",
        content=marker,
    )
    logger.info(
        f"Notifikasi konsultasi sesi {session.id} dikirim ke "
        f"{jumlah_terkirim}/{len(daftar_petugas)} petugas"
    )
    return True


###########################################################################
# AKSI PETUGAS
###########################################################################

async def handle_petugas_message(petugas, data):
    """Router semua pesan yang berasal dari nomor petugas."""
    if not petugas.is_active:
        logger.info(f"Pesan petugas nonaktif {petugas.notelp} diabaikan")
        return

    if not is_text_message(data):
        await send_simple_text(
            petugas.notelp,
            "Mohon maaf, saat ini hanya pesan teks yang dapat diproses.",
        )
        return

    text = data.message.strip()

    if text.lower() in ("/akhiri", "/end"):
        await akhiri_live_chat(petugas)
        return

    pilihan, session_id = parse_petugas_action(text)
    if pilihan is not None:
        await handle_petugas_choice(petugas, pilihan, session_id)
        return

    # Pesan bebas petugas -> diteruskan ke pengguna pada sesi live-nya.
    live = await get_live_session_by_handler(petugas.id)
    if live is None:
        await send_simple_text(petugas.notelp, TANPA_LIVE_TEXT)
        return

    await ChatMessage.aio_create(
        session=live,
        role="petugas",
        content=text,
    )
    await send_simple_text(live.phone, text)
    logger.info(
        f"Pesan petugas {petugas.id} diteruskan ke sesi {live.id}"
    )


async def akhiri_live_chat(petugas):
    live = await get_live_session_by_handler(petugas.id)
    if live is None:
        await send_simple_text(
            petugas.notelp,
            "Tidak ada sesi live chat aktif yang bisa diakhiri.",
        )
        return

    await end_handoff_session(live, petugas, alasan="/akhiri")


_petugas_choice_locks: dict[int, asyncio.Lock] = {}


def _petugas_choice_lock(petugas_id: int) -> asyncio.Lock:
    lock = _petugas_choice_locks.get(petugas_id)
    if lock is None:
        lock = asyncio.Lock()
        _petugas_choice_locks[petugas_id] = lock
    return lock


async def handle_petugas_choice(petugas, pilihan: int, session_id: int):
    # Serialkan pilihan per petugas agar dua balasan list yang datang hampir
    # bersamaan tidak membuka dua sesi live untuk petugas yang sama.
    async with _petugas_choice_lock(petugas.id):
        await _handle_petugas_choice(petugas, pilihan, session_id)


async def _handle_petugas_choice(petugas, pilihan: int, session_id: int):
    session = await get_session_by_id(session_id)

    if session is None:
        await send_simple_text(
            petugas.notelp,
            f"Mohon maaf, sesi #{session_id} tidak ditemukan.",
        )
        return

    # Handoff hanya untuk layanan Konsultasi Statistik (layanan = 1).
    if session.layanan != 1:
        await send_simple_text(
            petugas.notelp,
            f"Mohon maaf, sesi #{session.id} bukan sesi konsultasi statistik.",
        )
        return

    user = await get_user_by_phone(session.phone)
    nama = nama_pengguna(user, session.phone)

    # List kedaluwarsa: sesi sudah selesai.
    if session.is_done or session.mode == MODE_SELESAI:
        await send_simple_text(
            petugas.notelp,
            f"Mohon maaf, sesi #{session.id} sudah tidak aktif (sudah selesai).",
        )
        return

    # Opsi 3 boleh dilakukan siapa saja, termasuk sesi yang belum diambil.
    if pilihan == 3:
        await end_handoff_session(session, petugas, alasan="list")
        return

    if pilihan not in (1, 2):
        await send_simple_text(
            petugas.notelp,
            "Pilihan tidak dikenali. Silakan pilih dari list konsultasi.",
        )
        return

    # Petugas menekan ulang list untuk sesi yang sudah ia tangani sendiri:
    # cukup kirim ulang konfirmasi, jangan klaim dua kali.
    if session.handler_id == petugas.id:
        if session.mode == MODE_LIVE:
            await send_simple_text(
                petugas.notelp,
                LIVE_ON_TEXT.format(nama=nama, phone=session.phone),
            )
        else:
            await send_simple_text(
                petugas.notelp,
                MANUAL_ON_TEXT.format(nama=nama, phone=session.phone),
            )
        return

    # Sudah diambil petugas lain.
    if session.handler_id is not None:
        penangan = await get_petugas_by_id(session.handler_id)
        nama_penangan = penangan.nama if penangan else "petugas lain"
        await send_simple_text(
            petugas.notelp,
            f"Sesi ini sudah ditangani oleh {nama_penangan}.",
        )
        return

    # Satu petugas hanya boleh punya satu sesi live.
    if pilihan == 1:
        live = await get_live_session_by_handler(petugas.id)
        if live is not None and live.id != session.id:
            live_user = await get_user_by_phone(live.phone)
            await send_simple_text(
                petugas.notelp,
                f"Anda masih live chat dengan "
                f"{nama_pengguna(live_user, live.phone)}. "
                f"Akhiri sesi tersebut dulu.",
            )
            return

    mode_baru = MODE_LIVE if pilihan == 1 else MODE_MANUAL
    claimed = await claim_session(session.id, petugas.id, mode_baru)

    if not claimed:
        session = await get_session_by_id(session.id)
        penangan = None
        if session is not None and session.handler_id is not None:
            penangan = await get_petugas_by_id(session.handler_id)
        nama_penangan = penangan.nama if penangan else "petugas lain"
        await send_simple_text(
            petugas.notelp,
            f"Sesi ini sudah ditangani oleh {nama_penangan}.",
        )
        return

    session = await get_session_by_id(session.id)

    if mode_baru == MODE_LIVE:
        await send_simple_text(
            petugas.notelp,
            LIVE_ON_TEXT.format(nama=nama, phone=session.phone),
        )
        logger.info(
            f"Petugas {petugas.id} membuka live chat sesi {session.id}"
        )
    else:
        await send_simple_text(
            petugas.notelp,
            MANUAL_ON_TEXT.format(nama=nama, phone=session.phone),
        )
        logger.info(
            f"Petugas {petugas.id} memakai mode manual sesi {session.id}"
        )


###########################################################################
# PESAN PENGGUNA SAAT HANDOFF
###########################################################################

async def handle_user_handoff_message(session, data):
    """Pesan pengguna pada sesi layanan 1 yang sedang menunggu/live/manual."""
    session = await get_session_by_id(session.id)

    if (
        session is None
        or session.is_done
        or session.layanan != 1
        or session.mode == MODE_SELESAI
    ):
        logger.info("Pesan untuk sesi handoff yang sudah tidak aktif diabaikan")
        return

    user = await get_user_by_phone(session.phone)
    nama = nama_pengguna(user, session.phone)

    if not is_text_message(data):
        logger.info(
            f"Media dari {session.phone} pada sesi {session.id} tidak didukung"
        )
        if session.mode == MODE_LIVE:
            await send_simple_text(
                session.phone,
                "Mohon maaf, saat ini hanya pesan teks yang dapat "
                "diteruskan ke petugas. 🙏",
            )
            if session.handler_id is not None:
                handler = await get_petugas_by_id(session.handler_id)
                if handler is not None:
                    await send_simple_text(
                        handler.notelp,
                        f"{nama}: [mengirim media, tidak dapat diteruskan]",
                    )
        return

    text = data.message.strip()
    await ChatMessage.aio_create(
        session=session,
        role="user",
        content=text,
    )

    if session.mode != MODE_LIVE:
        # Mode menunggu / manual: simpan saja, jangan balas, jangan proses AI.
        return

    if session.handler_id is None:
        logger.warning(f"Sesi live {session.id} tidak punya handler")
        return

    handler = await get_petugas_by_id(session.handler_id)
    if handler is None:
        logger.warning(
            f"Handler sesi live {session.id} tidak ditemukan di tabel petugas"
        )
        return

    await send_simple_text(handler.notelp, f"{nama}: {text}")


###########################################################################
# AKHIR SESI
###########################################################################

async def end_handoff_session(session, petugas, alasan: str = "petugas"):
    user = await get_user_by_phone(session.phone)
    nama = nama_pengguna(user, session.phone)

    updated = await (
        ChatSession
        .update(
            mode=MODE_SELESAI,
            is_done=True,
            updated_at=datetime.now(),
        )
        .where(
            (ChatSession.id == session.id) &
            (ChatSession.is_done == False)
        )
        .aio_execute()
    )

    if updated != 1:
        await send_simple_text(
            petugas.notelp,
            f"Mohon maaf, sesi #{session.id} sudah tidak aktif.",
        )
        return

    await send_simple_text(
        petugas.notelp,
        LIVE_OFF_TEXT.format(nama=nama, phone=session.phone),
    )

    # Beri tahu petugas penangan jika sesi diakhiri oleh petugas lain.
    if session.handler_id is not None and session.handler_id != petugas.id:
        penangan = await get_petugas_by_id(session.handler_id)
        if penangan is not None:
            await send_simple_text(
                penangan.notelp,
                f"Sesi #{session.id} ({nama}) diakhiri oleh {petugas.nama}.",
            )

    teks = survey_text()
    await send_simple_text(session.phone, teks)
    await ChatMessage.aio_create(
        session=session,
        role="bot",
        content=teks,
    )

    logger.info(
        f"Sesi {session.id} diakhiri oleh petugas {petugas.id} ({alasan})"
    )


async def close_idle_handoff_sessions():
    """Tutup sesi live/manual yang idle, dengan notifikasi ke petugas."""
    cutoff = datetime.now() - timedelta(hours=HANDOFF_IDLE_HOURS)

    sessions = list(
        await ChatSession
        .select(
            ChatSession,
            fn.MAX(ChatMessage.created_at).alias("last_chat_time"),
        )
        .where(
            (ChatSession.layanan == 1) &
            (ChatSession.is_done == False) &
            (ChatSession.mode.in_([MODE_LIVE, MODE_MANUAL]))
        )
        .join(ChatMessage)
        .group_by(ChatSession)
        .having(fn.MAX(ChatMessage.created_at) < cutoff)
        .aio_execute()
    )

    for session in sessions:
        updated = await (
            ChatSession
            .update(
                mode=MODE_SELESAI,
                is_done=True,
                updated_at=datetime.now(),
            )
            .where(
                (ChatSession.id == session.id) &
                (ChatSession.is_done == False)
            )
            .aio_execute()
        )
        if updated != 1:
            continue

        user = await get_user_by_phone(session.phone)
        nama = nama_pengguna(user, session.phone)

        if session.handler_id is not None:
            handler = await get_petugas_by_id(session.handler_id)
            if handler is not None:
                await send_simple_text(
                    handler.notelp,
                    f"Sesi #{session.id} ditutup otomatis karena tidak ada "
                    f"aktivitas selama {HANDOFF_IDLE_HOURS} jam.\n"
                    f"Pengguna: {nama} ({session.phone})",
                )

        teks = survey_text()
        await send_simple_text(session.phone, teks)
        await ChatMessage.aio_create(
            session=session,
            role="bot",
            content=teks,
        )

        logger.info(
            f"Sesi handoff {session.id} ditutup otomatis "
            f"(idle {HANDOFF_IDLE_HOURS} jam)"
        )
