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

from .parse import xtb
from .parse import binance
from .registry import AssetRegistry
from .store.serialize import TxStore, load_wallet, save_wallet

DATA_DIR = "./data/raw"
TX_STORE_PATH = Path("./data/tx_store.json")


def _parse_binance(registry: AssetRegistry) -> list:
    out = []
    trades_path = Path(DATA_DIR, "trades.csv")
    converts_path = Path(DATA_DIR, "convert.csv")

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
        closed_sheet = xtb.find_sheet_by_prefix(path, "CLOSED POSITION")
        tx_closed = xtb.parse_closed_positions(path, closed_sheet)
        out += [tx for pos in tx_closed for tx in pos.to_transactions(registry)]
    except ValueError as e:
        print(f"  [Erreur XTB Closed] {e}")

    try:
        open_sheet = xtb.find_sheet_by_prefix(path, "OPEN POSITION")
        tx_open = xtb.parse_open_positions(path, open_sheet)
        out += [pos.to_transaction(registry) for pos in tx_open]
    except ValueError as e:
        print(f"  [Erreur XTB Open] {e}")

    return out


def main():
    print("=== CONSTRUCTION DU WALLET ===")

    # Wallet existant (fusion incrémentale) plutôt que repartir de zéro à
    # chaque run -- important dès que l'API de prix historiques a un coût
    # en temps (rate limit, latence réseau).
    wallet = load_wallet(TX_STORE_PATH)
    print(f"Wallet chargé : {len(wallet.transactions)} transaction(s) existante(s)")

    # Registre local pour cette passe de parsing -- ses ids ne servent
    # qu'à relier les transactions entre elles pendant le run ; ils sont
    # retraduits en symboles au moment de wallet.add_transactions().
    source_registry = AssetRegistry()

    new_transactions = []
    new_transactions += _parse_binance(source_registry)
    new_transactions += _parse_xtb_file(Path(DATA_DIR, "account.xlsx"), source_registry)
    new_transactions += _parse_xtb_file(Path(DATA_DIR, "account_pea.xlsx"), source_registry)

    added = wallet.add_transactions(new_transactions, source_registry)
    print(f"{added} nouvelle(s) transaction(s) ajoutée(s) (sur {len(new_transactions)} parsée(s), doublons ignorés)")

    save_wallet(wallet, TX_STORE_PATH)
    print(f"Wallet sauvegardé : {TX_STORE_PATH} ({len(wallet.transactions)} transaction(s) au total)")


if __name__ == "__main__":
    main()
