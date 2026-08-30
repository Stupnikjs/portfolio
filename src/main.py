"""
Script de test réel pour les parsers Binance et XTB.
Lit tes vrais fichiers de données et affiche le résultat.
"""
import os
from pathlib import Path
from datetime import datetime

# Imports relatifs de ton projet
from .registry import AssetRegistry
from .schema import Transaction
from . import binance, xtb, prices

def print_transactions(title: str, transactions: list[Transaction]):
    print(f"\n{'='*60}")
    print(f" {title} ({len(transactions)} transactions) ")
    print(f"{'='*60}")
    for tx in transactions:
        print(f"  [{tx.time.strftime('%Y-%m-%d')}] {tx.kind.value.upper():<5} | {tx.quantity:<8} {tx.asset_id:<3} | Prix: {tx.price} EUR | Fichier: {os.path.basename(tx.source_file)}")

def main():
    print("=== DÉMARRAGE DU TEST DES PARSERS ===")
    
    # 1. Chemins vers tes vrais fichiers
    binance_trades = Path("./data/trades.csv")
    binance_converts = Path("./data/convert.csv")
    xtb_file = Path("./data/account.xlsx")
    
    # 2. Initialiser le registre
    registry = AssetRegistry()
    
    # 3. Tester Binance (on vérifie si les fichiers existent avant de lancer)
    if binance_trades.exists():
        print("\nLecture des Trades Binance...")
        tx_trades = binance.parse_trades(binance_trades, registry)
        print_transactions("BINANCE - TRADES", tx_trades)
    else:
        print(f"\n[Omis] Fichier introuvable : {binance_trades}")
        
    if binance_converts.exists():
        print("\nLecture des Converts Binance...")
        tx_converts = binance.parse_converts(binance_converts, registry)
        print_transactions("BINANCE - CONVERTS", tx_converts)
    else:
        print(f"\n[Omis] Fichier introuvable : {binance_converts}")
    
    # 4. Tester XTB
    if xtb_file.exists():
        print("\nLecture des positions XTB...")
        try:
            closed_sheet = xtb.find_sheet_by_prefix(xtb_file, "CLOSED POSITION HISTORY")
            tx_closed = xtb.parse_closed_positions(xtb_file, closed_sheet)
            tx_closed_flat = [tx for pos in tx_closed for tx in pos.to_transactions(registry)]
            print_transactions("XTB - CLOSED POSITIONS", tx_closed_flat)
        except ValueError as e:
            print(f"  [Erreur XTB Closed] {e}")

        try:
            open_sheet = xtb.find_sheet_by_prefix(xtb_file, "OPEN POSITION 29072026")
            tx_open = xtb.parse_open_positions(xtb_file, open_sheet)
            tx_open_flat = [pos.to_transaction(registry) for pos in tx_open]
            print_transactions("XTB - OPEN POSITIONS", tx_open_flat)
        except ValueError as e:
            print(f"  [Erreur XTB Open] {e}")
    else:
        print(f"\n[Omis] Fichier introuvable : {xtb_file}")
    
    # 5. Afficher le registre final
    print(f"\n{'='*60}")
    print(f" REGISTRE D'ACTIFS CRÉÉ ")
    print(f"{'='*60}")
    for asset in registry.get_all_assets():
        print(f"  ID: {asset.id:<2} | Symbole: {asset.symbol:<10} | Type: {asset.kind.value}")
    
    print("\nTest terminé !")

if __name__ == "__main__":
    main()