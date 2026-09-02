"""
build_wallet.py

Construit (ou met à jour) wallet.json à partir des exports bruts dans
./data/raw/. Remplace le rôle "démo" de l'ancien main.py par une vraie
étape de persistance : parse -> fusion dans le Wallet -> save_wallet.

Ré-exécutable sans risque : le dédoublonnage par external_id (voir
store/wallet_store.py) garantit qu'un même fichier réimporté ne crée pas
de doublons.
"""

from pathlib import Path

from .parse import binance, xtb, manual
from .store.serialize import TxStore, load_wallet, save_wallet
from .schema import Platform, AssetKind
from .market.tickers import resolve_ticker 
from .ledger.portfolio import portfolio_snapshot_at
from datetime import datetime, timezone

DATA_DIR = "./data/raw"
MANUAL_PATH = Path(DATA_DIR, "manual_tx.json")
TX_STORE_PATH = Path("./data/tx_store.json")
ACCOUNTS_PATH = Path(DATA_DIR, "accounts")

def _parse_binance() -> list:
    out = []
    trades_path = Path(ACCOUNTS_PATH, "trades.csv")
    converts_path = Path(ACCOUNTS_PATH, "convert.csv")

    if trades_path.exists():
        print(f"Lecture Binance Trades : {trades_path}")
        out += binance.parse_trades(trades_path)
    else:
        print(f"[Omis] Fichier introuvable : {trades_path}")

    if converts_path.exists():
        print(f"Lecture Binance Converts : {converts_path}")
        out += binance.parse_converts(converts_path)
    else:
        print(f"[Omis] Fichier introuvable : {converts_path}")

    return out


def _parse_xtb_file(path: Path) -> list:
    out = []
    if not path.exists():
        print(f"[Omis] Fichier introuvable : {path}")
        return out

    print(f"Lecture XTB : {path}")
    try:
        closed_sheet = xtb.find_sheet_by_prefix(path, "Closed Position")
        tx_closed = xtb.parse_closed_positions(path, closed_sheet)
        out += [tx for pos in tx_closed for tx in pos.to_transactions()]
    except ValueError as e:
        print(f"  [Erreur XTB Closed] {e}")

    try:
        open_sheet = xtb.find_sheet_by_prefix(path, "Open Position")
        tx_open = xtb.parse_open_positions(path, open_sheet)
        out += [pos.to_transaction() for pos in tx_open]
    except ValueError as e:
        print(f"  [Erreur XTB Open] {e}")

    try:
        cash_sheet = xtb.find_sheet_by_prefix(path, "Cash")
        out += xtb.parse_cash_operations(path, cash_sheet)
    except ValueError as e:
        print(f"  [Erreur XTB Cash] {e}")

    return out


def main():
    print("=== CONSTRUCTION DU WALLET ===")

    tx_store = load_wallet(TX_STORE_PATH)
    print(f"Wallet chargé : {len(tx_store.transactions)} transaction(s) existante(s)")


    new_transactions = []
    xtb_tx = []
    new_transactions += _parse_binance()
    xtb_tx += _parse_xtb_file(Path(ACCOUNTS_PATH, "account.xlsx") )
    xtb_tx += _parse_xtb_file(Path(ACCOUNTS_PATH, "account_pea.xlsx") )

    
    _ = tx_store.add_transactions(new_transactions)
    _ = tx_store.add_transactions(xtb_tx)
    replaced = tx_store.replace_platform(Platform.XTB, xtb_tx)
    print(f"XTB : {replaced} transaction(s) (remplacement complet)")

    manual_tx = manual.parse_manual(MANUAL_PATH)
    replaced = tx_store.replace_platform(Platform.MANUAL, manual_tx)


    # ---------------------------------------------------------
    # RÉSOLUTION DES TICKERS MANQUANTS
    # On parcourt les actifs connus du wallet. S'ils n'ont pas encore
    # de ticker résolé (et ne sont pas du Cash), on interroge les APIs.
    # ---------------------------------------------------------
    print("\n=== RÉSOLUTION DES TICKERS ===")
    resolved = 0
    skipped = 0
    failed = 0
    
    for symbol, asset in tx_store.assets.items():
        if asset.kind == AssetKind.CASH:
            skipped += 1
            continue
            
        if asset.identifiers.ticker:
            skipped += 1
            continue
            
        ticker = resolve_ticker(symbol, asset.kind)
        if ticker:
            asset.identifiers.ticker = ticker
            print(f"  ✓ {symbol:<12} -> {ticker}")
            resolved += 1
        else:
            print(f"  ✗ {symbol:<12} : ticker introuvable")
            failed += 1
    
    save_wallet(tx_store, TX_STORE_PATH)
  
    
    print("\n=== VALORISATION ACTUELLE ===")
    snapshot = portfolio_snapshot_at(tx_store)
    print(f"Date: {snapshot['date']}")
    print(f"Valeur totale: {snapshot['total_value_eur']:,.2f} EUR")
    print("Détail par actif:")

    for asset in snapshot['assets']:
        if asset['value_eur'] > 0.01: # On cache les poussières
            print(f"  - {asset['symbol']:<10} ({asset['kind']:<6}) | Qty: {asset['quantity']:<10.4f} | Prix: {asset['price_eur']:<10.2f} | Valeur: {asset['value_eur']:>10,.2f} EUR")

    # Exemple à une date passée :
    print("\n=== VALORISATION AU 01 JANVIER 2024 ===")
    past_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    past_snapshot = portfolio_snapshot_at(tx_store, past_date)
    print(f"Valeur totale: {past_snapshot['total_value_eur']:,.2f} EUR")

if __name__ == "__main__":
    main()
