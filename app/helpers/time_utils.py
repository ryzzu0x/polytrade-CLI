from datetime import datetime, timedelta, timezone

def get_current_interval_timestamp(minutes_interval: int) -> int:
    """
    Mendapatkan Unix Timestamp untuk awal interval waktu saat ini.
    Misal: Jika sekarang 10:52 dan interval 5, maka mengembalikan timestamp untuk 10:50.
    """
    now = datetime.now(timezone.utc)
    minutes = now.minute
    remainder = minutes % minutes_interval
    
    # Kurangi menit dengan sisa bagi untuk mendapatkan titik awal interval (pembulatan ke bawah)
    current_time = now - timedelta(minutes=remainder)
    current_time = current_time.replace(second=0, microsecond=0)
    
    return int(current_time.timestamp())

def generate_polymarket_slug(asset: str, timeframe: str) -> str:
    """
    Merakit slug URL untuk Metode C. Contoh output: btc-updown-5m-1780372800
    """
    minutes = int(''.join(filter(str.isdigit, timeframe)))
    
    timestamp = get_current_interval_timestamp(minutes)
    slug = f"{asset.lower()}-updown-{timeframe.lower()}-{timestamp}"
    
    return slug