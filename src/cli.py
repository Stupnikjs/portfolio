"""
build_wallet.py

Construit (ou met à jour) wallet.json à partir des exports bruts dans
./data/raw/. Remplace le rôle "démo" de l'ancien main.py par une vraie
étape de persistance : parse -> fusion dans le Wallet -> save_wallet.

Ré-exécutable sans risque : le dédoublonnage par external_id (voir
store/wallet_store.py) garantit qu'un même fichier réimporté ne crée pas
de doublons.
"""

import os
from pathlib import Path

from .parse import binance, xtb, manual
from .registry import AssetRegistry
from .store.serialize import TxStore, load_wallet, save_wallet
from .ledger.positions import holdings_at
from .schema import Platform

DATA_DIR = "./data/raw"
MANUAL_PATH = Path(DATA_DIR, "manual_tx.json")
TX_STORE_PATH = Path("./data/tx_store.json")
ACCOUNTS_PATH = Path(DATA_DIR, "accounts")

def _parse_binance(registry: AssetRegistry) -> list:
    out = []
    trades_path = Path(ACCOUNTS_PATH, "trades.csv")
    converts_path = Path(ACCOUNTS_PATH, "convert.csv")

    if trades_path.exists():
        print(f"Lecture Binance Trades : {trades_path}")
        out += binance.parse_trades(trades_path, registry)
    else:
        print(f"[Omis] Fichier introuvable : {trades_path}")

    if converts_path.exists():
        print(f"Lecture Binance Converts : {converts_path}")
        out += binance.parse_converts(converts_path, registry)
    else:
        print(f"[Omis] Fichier introuvable : {converts_path}")

    return out


def _parse_xtb_file(path: Path, registry: AssetRegistry) -> list:
    out = []
    if not path.exists():
        print(f"[Omis] Fichier introuvable : {path}")
        return out

    print(f"Lecture XTB : {path}")
    try:
        closed_sheet = xtb.find_sheet_by_prefix(path, "Closed Position")
        tx_closed = xtb.parse_closed_positions(path, closed_sheet)
        out += [tx for pos in tx_closed for tx in pos.to_transactions(registry)]
    except ValueError as e:
        print(f"  [Erreur XTB Closed] {e}")

    try:
        open_sheet = xtb.find_sheet_by_prefix(path, "Open Position")
        tx_open = xtb.parse_open_positions(path, open_sheet)
        out += [pos.to_transaction(registry) for pos in tx_open]
    except ValueError as e:
        print(f"  [Erreur XTB Open] {e}")

    try:
        cash_sheet = xtb.find_sheet_by_prefix(path, "Cash")
        out += xtb.parse_cash_operations(path, cash_sheet, registry)
    except ValueError as e:
        print(f"  [Erreur XTB Cash] {e}")

    return out


def main():
    print("=== CONSTRUCTION DU WALLET ===")

    tx_store = load_wallet(TX_STORE_PATH)
    print(f"Wallet chargé : {len(tx_store.transactions)} transaction(s) existante(s)")


    source_registry = AssetRegistry()

    new_transactions = []
    xtb_tx = []
    new_transactions += _parse_binance(source_registry)
    xtb_tx += _parse_xtb_file(Path(ACCOUNTS_PATH, "account.xlsx"), source_registry)
    xtb_tx += _parse_xtb_file(Path(ACCOUNTS_PATH, "account_pea.xlsx"), source_registry)

    
    _ = tx_store.add_transactions(new_transactions, source_registry)
    _ = tx_store.add_transactions(xtb_tx, source_registry)
    replaced = tx_store.replace_platform(Platform.XTB, xtb_tx, source_registry)
    print(f"XTB : {replaced} transaction(s) (remplacement complet)")

    manual_tx = manual.parse_manual(MANUAL_PATH, source_registry)
    replaced = tx_store.replace_platform(Platform.MANUAL, manual_tx, source_registry)

    save_wallet(tx_store, TX_STORE_PATH)
    print(f"Wallet sauvegardé : {TX_STORE_PATH} ({len(tx_store.transactions)} transaction(s) au total)")

    holdings = holdings_at(tx_store=tx_store)
    print(holdings)

if __name__ == "__main__":
    main()
