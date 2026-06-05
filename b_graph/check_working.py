import requests
from datetime import datetime, time
from _global import shared_cache
import httpx
import asyncio
from _global import logger

async def is_working_hours(dt_to_check):
    start_time = time(8, 0)
    end_time = time(15, 0)
    return start_time <= dt_to_check.time() <= end_time

async def is_weekday(dt_to_check):
    """Mengecek apakah hari Senin - Jumat (0 = Senin, 5 = Sabtu, 6 = Minggu)"""
    return dt_to_check.weekday() < 5

async def is_holiday(dt_to_check):
    """Mengecek apakah tanggal merah dari API"""
    year = dt_to_check.year

    holidays = []

    if "holidays_"+str(year) in shared_cache:
        holidays = shared_cache.get("holidays_"+str(year))
    else:
        url = f"https://tanggalmerah.upset.dev/api/holidays?year={year}"
        try:
            # Menggunakan AsyncClient untuk melakukan request asinkron
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                
                # Memastikan response OK (mirip dengan requests)
                response.raise_for_status() 
                
                data = response.json()['data']

                # Logika parsing data kamu tetap sama persis
                if isinstance(data, list):
                    if len(data) > 0 and isinstance(data[0], dict):
                        holidays = [item.get('date') for item in data if 'date' in item]
                    else:
                        holidays = data
                else:
                    holidays = []
                

            shared_cache.set("holidays_"+str(year), holidays)
                
        except requests.exceptions.RequestException as e:
            logger.info(f"[Peringatan] Gagal mengambil data dari API: {e}")
            # Asumsi fail-safe: jika API mati, anggap bukan hari libur
            return False 
    
    date_str = dt_to_check.strftime("%Y-%m-%d")
    return date_str in holidays

async def check_work_status(dt_to_check=None):
    """Fungsi utama untuk memvalidasi semua kondisi"""
    if dt_to_check is None:
        dt_to_check = datetime.now()
        
    # 1. Validasi Jam Kerja
    if not is_working_hours(dt_to_check):
        return False, "Di luar jam kerja (Hanya aktif 08.00 - 15.00)"
        
    # 2. Validasi Hari Kerja (Bukan akhir pekan)
    if not is_weekday(dt_to_check):
        return False, "Bukan hari kerja (Akhir pekan)"
        
    # 3. Validasi Tanggal Merah
    if is_holiday(dt_to_check):
        return False, "Hari libur nasional / Tanggal merah"
        
    return True, "Jam operasional aktif (Saat ini adalah hari dan jam kerja)"