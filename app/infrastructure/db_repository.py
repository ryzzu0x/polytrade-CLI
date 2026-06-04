import asyncpg
from datetime import datetime
from app.domain.models import MarketHistoryDB

class PostgresRepository:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(dsn=self.dsn)
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS market_history (
                        id SERIAL PRIMARY KEY,
                        condition_id VARCHAR(100) UNIQUE,
                        asset VARCHAR(10),
                        timeframe VARCHAR(10),
                        start_time TIMESTAMP WITH TIME ZONE,
                        end_time TIMESTAMP WITH TIME ZONE,
                        winning_outcome VARCHAR(15),
                        total_volume NUMERIC(15,2),
                        asset_price_start NUMERIC(15,2),
                        asset_price_end NUMERIC(15,2),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            print("\n[DATABASE] 🟢 Koneksi ke PostgreSQL Berhasil dan Tabel Siap!")
        except Exception as e:
            print(f"\n[DATABASE ERROR] 🔴 Gagal koneksi ke PostgreSQL: {e}")

    def _format_time_string(self, time_val):
        """Membypass Python Datetime: Kita paksa kirim string agar Postgres yang membaca waktunya"""
        if not time_val: 
            return None
            
        # Jika berupa datetime, jadikan string ISO
        if isinstance(time_val, datetime):
            time_str = time_val.isoformat()
        else:
            time_str = str(time_val).strip()
            
        # Pastikan ada penanda UTC ('Z' atau '+') agar Postgres tidak salah zona
        if not time_str.endswith("Z") and "+" not in time_str:
            time_str += "Z"
            
        return time_str

    async def save_market_history(self, history: MarketHistoryDB):
        if not self.pool: return
            
        query = """
            INSERT INTO market_history 
            (condition_id, asset, timeframe, start_time, end_time, winning_outcome, total_volume, asset_price_start, asset_price_end)
            VALUES ($1, $2, $3, $4::text::timestamptz, $5::text::timestamptz, $6, $7, $8, $9)
            ON CONFLICT (condition_id) DO NOTHING;
        """
        try:
            start_str = self._format_time_string(history.start_time)
            end_str = self._format_time_string(history.end_time)

            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    history.condition_id, history.asset, history.timeframe,
                    start_str, end_str, 
                    history.winning_outcome, history.total_volume,
                    history.asset_price_start, history.asset_price_end
                )
            # PERBAIKAN TAMPILAN
            print(f"\r{' ' * 80}\r[DATABASE] 💾 Data Tersimpan! (Vol: ${history.total_volume:,.2f} | Status: {history.winning_outcome})")
        except Exception as e:
            print(f"\r{' ' * 80}\r[DATABASE ERROR] 🔴 Gagal menyimpan data: {e}")

    async def update_market_winner(self, condition_id: str, winning_outcome: str):
        if not self.pool: return
        query = "UPDATE market_history SET winning_outcome = $1 WHERE condition_id = $2"
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, winning_outcome, condition_id)
            # PERBAIKAN TAMPILAN
            print(f"\r{' ' * 80}\r[BACKGROUND DB] ✅ Market {condition_id[:8]}... diperbarui menjadi: {winning_outcome}!")
        except Exception as e:
            print(f"\r{' ' * 80}\r[DATABASE ERROR] 🔴 Gagal update pemenang: {e}")