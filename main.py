import asyncio
import os
from config.settings import DATABASE_URL
from app.application.use_cases import FetchPolymarketEventUseCase, StreamPolymarketDataUseCase
from app.infrastructure.db_repository import PostgresRepository
from app.infrastructure.binance_api import BinanceRESTClient

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("=== PolyTrade-CLI (Core Engine 24/7) ===")
    print("=" * 40 + "\n")

def select_from_menu(title: str, options: list) -> str:
    print(title)
    print("-" * 30)
    for idx, option in enumerate(options, 1):
        print(f"[{idx}] {option}")
    print("-" * 30)
    
    while True:
        try:
            choice = input("Pilih nomor (atau Ctrl+C untuk batal): ").strip()
            if 1 <= int(choice) <= len(options):
                return options[int(choice) - 1]
            print(f"🔴 Pilihan tidak valid.")
        except ValueError:
            print("🔴 Input harus berupa angka.")
        except KeyboardInterrupt:
            exit()

async def main():
    clear_screen()
    print_header()
    asset_input = select_from_menu("Pilih Asset:", ['BTC', 'SOL', 'HYPE', 'BNB', 'XRP', 'DOGE', 'ETH'])
    
    clear_screen()
    print_header()
    print(f"[✓] Asset terpilih: {asset_input}\n")
    timeframe_input = select_from_menu("Pilih Timeframe:", ['5m', '15m'])
    
    clear_screen()
    print_header()
    
    # 1. INISIASI DATABASE
    db_repo = PostgresRepository(dsn=DATABASE_URL)
    await db_repo.connect()
    
    fetch_use_case = FetchPolymarketEventUseCase()
    stream_use_case = StreamPolymarketDataUseCase(db_repo=db_repo)
    binance_client = BinanceRESTClient()

    # INFINITE LOOP UNTUK AUTO-ROLLOVER
    while True:
        try:
            print(f"\n[SYSTEM] Memulai pencarian market untuk: {asset_input} ({timeframe_input})")
            
            # FASE 1: Cari Market Polymarket & Harga Binance
            event_result = await fetch_use_case.execute(asset=asset_input, timeframe=timeframe_input)
            binance_price = await binance_client.get_current_price(asset_input)
            
            print("\n" + "=" * 50)
            print(f"[BINANCE] {asset_input} Current Spot Price: ${binance_price:,.2f}")
            print("=" * 50)
            print(f"[POLYMARKET] Name : {event_result.name}")

            if event_result.is_closed or not event_result.is_active:
                print("[SYSTEM] Market saat ini tertutup. Menunggu siklus selanjutnya dalam 10 detik...")
                await asyncio.sleep(10)
                continue # Mengulang loop pencarian

            # FASE 2: Streaming
            print("[SYSTEM] Menghubungkan ke WebSocket Polymarket... (Tekan Ctrl+C untuk Stop)\n")
            market_state = {"YES": {"bid": 0.0, "ask": 0.0}, "NO": {"bid": 0.0, "ask": 0.0}}

            async for update in stream_use_case.execute(event_result, asset_input, timeframe_input, binance_price):
                
                if update["type"] == "ui_update":
                    data = update["data"]
                    top_bid = data.bids[0].price if data.bids else market_state[data.asset_name]["bid"]
                    top_ask = data.asks[0].price if data.asks else market_state[data.asset_name]["ask"]
                    
                    market_state[data.asset_name]["bid"] = top_bid
                    market_state[data.asset_name]["ask"] = top_ask

                    print(f"\r[LIVE] YES | B: {market_state['YES']['bid']:.2f} A: {market_state['YES']['ask']:.2f}  ||  NO | B: {market_state['NO']['bid']:.2f} A: {market_state['NO']['ask']:.2f}  ||  Vol: ${data.current_volume:,.2f}    ", end="", flush=True)

                elif update["type"] == "system_log":
                    # Menghapus baris [LIVE] sementara agar log tercetak rapi
                    print(f"\r{' ' * 80}\r[EVENT] {update['message']}")

                elif update["type"] == "rollover":
                    print(f"\r{' ' * 80}\r[SYSTEM] Melakukan Rollover Otomatis ke Market Selanjutnya...\n")
                    break # Pecah stream loop, kembali ke Phase 1 di atas!

        except asyncio.CancelledError:
            print("\n[SYSTEM] Streaming dihentikan.")
            break
        except KeyboardInterrupt:
            print("\n[SYSTEM] Keluar dari aplikasi.")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("[SYSTEM] Mencoba kembali dalam 5 detik...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass