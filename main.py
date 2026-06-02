# main.py
import asyncio
import os
from app.application.use_cases import FetchPolymarketEventUseCase

def clear_screen():
    """Membersihkan layar terminal sesuai dengan OS (Windows/Unix)."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Mencetak header aplikasi."""
    print("=== PolyTrade-CLI (Phase 1: Discovery) ===")
    print("=" * 42 + "\n")

def select_from_menu(title: str, options: list) -> str:
    """Menampilkan menu pilihan dan menangkap input angka."""
    print(title)
    print("-" * 30)
    for idx, option in enumerate(options, 1):
        print(f"[{idx}] {option}")
    print("-" * 30)
    
    while True:
        try:
            choice = input("Pilih nomor (atau Ctrl+C untuk batal): ").strip()
            choice_int = int(choice)
            
            if 1 <= choice_int <= len(options):
                return options[choice_int - 1]
            else:
                print(f"🔴 Pilihan tidak valid. Harap masukkan angka antara 1 dan {len(options)}.")
        except ValueError:
            print("🔴 Input harus berupa angka.")
        except KeyboardInterrupt:
            print("\nMembatalkan operasi...")
            exit()

async def main():
    # 1. Tampilkan List Asset
    clear_screen()
    print_header()
    daftar_asset = ['BTC', 'SOL', 'HYPE', 'BNB', 'XRP', 'DOGE', 'ETH']
    asset_input = select_from_menu("Pilih Asset yang ingin dipantau:", daftar_asset)
    
    # 2. Tampilkan List Timeframe (Layar dibersihkan dulu)
    clear_screen()
    print_header()
    print(f"[✓] Asset terpilih: {asset_input}\n")
    daftar_timeframe = ['5m', '15m']
    timeframe_input = select_from_menu("Pilih Timeframe Polymarket:", daftar_timeframe)
    
    # 3. Proses Pencarian API (Layar dibersihkan dulu)
    clear_screen()
    print_header()
    print(f"[SYSTEM] Memulai pencarian untuk: {asset_input} pada timeframe {timeframe_input}")
    print("-" * 50)
    
    use_case = FetchPolymarketEventUseCase()
    
    try:
        # Menjalankan workflow Fase 1
        event_result = await use_case.execute(asset=asset_input, timeframe=timeframe_input)
        
        # Logika Penentuan Status Visual
        if event_result.is_active and not event_result.is_closed:
            status_visual = "🟢 ACTIVE"
        else:
            status_visual = "🔴 CLOSED"

        # Log Checkpoint
        print("\n[SYSTEM] Market Found!")
        print(f"[SYSTEM] Name          : {event_result.name}")
        print(f"[SYSTEM] Slug          : {event_result.slug}")
        print(f"[SYSTEM] Status        : {status_visual}")
        print(f"[SYSTEM] Token ID (YES): {event_result.token_id_yes}")
        print(f"[SYSTEM] Token ID (NO) : {event_result.token_id_no}")
        print("\n[SYSTEM] Proceeding to WebSocket connection... (Ready for Phase 2)")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    asyncio.run(main())