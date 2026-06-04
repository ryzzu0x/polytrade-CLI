# config/settings.py
import os
from dotenv import load_dotenv

# Memuat variabel dari file .env ke dalam sistem
load_dotenv()

# Mengambil URL Database, berikan nilai default kosong atau error jika tidak ditemukan
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("🔴 ERROR: DATABASE_URL tidak ditemukan di file .env!")