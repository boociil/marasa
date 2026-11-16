"""Tes sederhana get_petugas_bertugas tanpa menyentuh database produksi.

Cara jalan (dari root repo):
    venv/bin/python tests/test_jadwal_petugas.py

Tes memakai SQLite in-memory. Model di-bind ulang ke SQLite, dan eksekusi
async query diarahkan ke eksekusi sinkron SQLite khusus proses tes ini.
"""

import asyncio
import os
import sys
from datetime import datetime, time, timezone
from pathlib import Path

# Pastikan import `db.models` tidak gagal karena env DB_PORT kosong.
os.environ.setdefault("DB_DATABASE", "test_jadwal")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peewee import SqliteDatabase
from peewee_async.aio_model import AioQueryMixin

from db.models import JadwalPetugas, Petugas, get_petugas_bertugas


# ---------------------------------------------------------------------------
# Arahkan aio_execute ke eksekusi sinkron SQLite (hanya untuk tes ini).
# ---------------------------------------------------------------------------
async def _aio_execute_sync(self, database=None):
    return list(self)


AioQueryMixin.aio_execute = _aio_execute_sync


test_db = SqliteDatabase(":memory:")
test_db.bind([Petugas, JadwalPetugas])
test_db.connect()
test_db.create_tables([Petugas, JadwalPetugas])


# ---------------------------------------------------------------------------
# Data tiruan
# ---------------------------------------------------------------------------
pagi = Petugas.create(nama="Petugas Pagi", notelp="620000000001", is_active=True)
siang = Petugas.create(nama="Petugas Siang", notelp="620000000002", is_active=True)
nonaktif = Petugas.create(nama="Petugas Nonaktif", notelp="620000000003", is_active=False)
overlap = Petugas.create(nama="Petugas Overlap", notelp="620000000004", is_active=True)

# Senin pagi + Selasa pagi.
JadwalPetugas.create(
    petugas=pagi, hari=1, sesi="pagi",
    jam_mulai=time(8, 0), jam_selesai=time(12, 0),
)
JadwalPetugas.create(
    petugas=pagi, hari=2, sesi="pagi",
    jam_mulai=time(8, 0), jam_selesai=time(12, 0),
)

# Senin siang.
JadwalPetugas.create(
    petugas=siang, hari=1, sesi="siang",
    jam_mulai=time(12, 0), jam_selesai=time(15, 0),
)

# Nonaktif: punya jadwal Senin pagi, harus tidak pernah muncul.
JadwalPetugas.create(
    petugas=nonaktif, hari=1, sesi="pagi",
    jam_mulai=time(8, 0), jam_selesai=time(12, 0),
)

# Rabu: dua baris yang tumpang tindih (08:00-13:00 dan 12:00-15:00).
# Pada 12:30 keduanya cocok; hasil harus unik (satu kali).
JadwalPetugas.create(
    petugas=overlap, hari=3, sesi="pagi",
    jam_mulai=time(8, 0), jam_selesai=time(13, 0),
)
JadwalPetugas.create(
    petugas=overlap, hari=3, sesi="siang",
    jam_mulai=time(12, 0), jam_selesai=time(15, 0),
)


def phones(rows):
    return [row.notelp for row in rows]


async def main():
    # 9 November 2026 = Senin; 10 November 2026 = Selasa; 11 November = Rabu.
    kasus = [
        ("Senin 07:59 (sebelum pagi)", datetime(2026, 11, 9, 7, 59), []),
        ("Senin 08:00 (pagi)", datetime(2026, 11, 9, 8, 0), ["620000000001"]),
        ("Senin 11:59 (masih pagi)", datetime(2026, 11, 9, 11, 59), ["620000000001"]),
        ("Senin 12:00 (siang)", datetime(2026, 11, 9, 12, 0), ["620000000002"]),
        ("Senin 15:00 (selesai)", datetime(2026, 11, 9, 15, 0), []),
        ("Senin 09:00 (nonaktif tidak ikut)", datetime(2026, 11, 9, 9, 0), ["620000000001"]),
        ("Selasa 08:30 (pagi, jadwal berbeda hari)", datetime(2026, 11, 10, 8, 30), ["620000000001"]),
        ("Rabu 12:30 (dua baris cocok, tidak duplikat)", datetime(2026, 11, 11, 12, 30), ["620000000004"]),
        (
            "Senin 01:00 UTC = 09:00 WITA",
            datetime(2026, 11, 9, 1, 0, tzinfo=timezone.utc),
            ["620000000001"],
        ),
    ]

    lulus = 0
    for label, waktu, expected in kasus:
        hasil = phones(await get_petugas_bertugas(waktu))
        status = "OK  " if hasil == expected else "GAGAL"
        print(f"[{status}] {label}: {hasil} (harap: {expected})")
        assert hasil == expected, f"{label}: {hasil} != {expected}"
        lulus += 1

    print(f"\nSEMUA TES LULUS ({lulus} kasus)")


if __name__ == "__main__":
    asyncio.run(main())
