from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set


from ..schema import (
    AssetIdentifiers,
    Asset,
    AssetKind,
    Platform,
    Transaction,
    TransactionKind,
)

TX_STORE_VERSION = 1


# ---------------------------------------------------------------------------
# Sérialisation Transaction <-> dict (par symbole)
# ---------------------------------------------------------------------------

def _transaction_to_dict(tx: Transaction) -> dict:
    
    return {
        "platform": tx.platform.value,
        "account_label": tx.account_label,
        "kind": tx.kind.value,
        "asset": tx.asset.symbol,
        "quantity": tx.quantity,
        "price": tx.price,
        "value_eur": tx.value_eur,
        "amount": tx.amount,
        "quote_currency": tx.quote_currency,
        "time": tx.time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "external_id": tx.external_id,
        "remark": tx.remark,
        "source_file": tx.source_file,
    }


def _transaction_from_dict(data: dict, tx_store:TxStore,  assets_meta: Dict[str, dict]) -> Transaction:
    symbol = data["asset"]
    meta = assets_meta[symbol]
    asset = tx_store.find_or_create_asset(
        symbol, meta["name"], AssetKind(meta["kind"]),
        meta["ref_currency"], AssetIdentifiers(**meta["identifiers"]),
    )
    return Transaction(
        platform=Platform(data["platform"]),
        account_label=data["account_label"],
        kind=TransactionKind(data["kind"]),
        asset=asset,
        quantity=data["quantity"],
        price=data["price"],
        value_eur=data["value_eur"],
        amount=data["amount"],
        quote_currency=data["quote_currency"],
        time=datetime.fromisoformat(data["time"].replace("Z", "+00:00")),
        external_id=data["external_id"],
        remark=data["remark"],
        source_file=data["source_file"],
    )


# ---------------------------------------------------------------------------
# Wallet : conteneur en mémoire
# ---------------------------------------------------------------------------

class TxStore:
    def __init__(self) -> None:
        self.assets: Dict[str, Asset] = {}
        self.transactions: List[Transaction] = []
        self._known_external_ids: Set[str] = set()

    def find_or_create_asset(
        self, symbol: str, name: str, kind: AssetKind,
        ref_currency: str, identifiers: AssetIdentifiers,
    ) -> Asset:
        """Retourne l'Asset canonique pour ce symbole, le créant si besoin.
        Si un Asset existe déjà pour ce symbole, ses métadonnées font foi
        (comportement identique à l'ancien AssetRegistry.find_or_create)."""
        existing = self.assets.get(symbol)
        if existing is not None:
            return existing
        asset = Asset(symbol=symbol, name=name, kind=kind,
                       ref_currency=ref_currency, identifiers=identifiers)
        self.assets[symbol] = asset
        return asset

    def add_transactions(self, new_transactions: List[Transaction]) -> int:
        """Fusionne des transactions fraîchement parsées dans le wallet.

        Chaque `tx.asset` vient d'un parseur et est une instance locale à
        ce run : on la retraduit vers l'Asset canonique du store via le
        symbole, puis on clone la transaction avec `dataclasses.replace`
        pour n'avoir qu'un seul point à maintenir si Transaction gagne un
        champ plus tard.
        """
        added = 0
        for tx in new_transactions:
            if tx.external_id is not None and tx.external_id in self._known_external_ids:
                continue

            local_asset = self.find_or_create_asset(
                tx.asset.symbol, tx.asset.name, tx.asset.kind,
                tx.asset.ref_currency, tx.asset.identifiers,
            )
            self.transactions.append(replace(tx, asset=local_asset))
            if tx.external_id is not None:
                self._known_external_ids.add(tx.external_id)
            added += 1

        return added

    def replace_platform(self, platform: Platform, new_transactions: list[Transaction]) -> int:
        self.transactions = [tx for tx in self.transactions if tx.platform != platform]
        self._known_external_ids = {
            tx.external_id for tx in self.transactions if tx.external_id is not None
        }
        return self.add_transactions(new_transactions)


# ---------------------------------------------------------------------------
# Chargement / sauvegarde JSON
# ---------------------------------------------------------------------------

def load_tx_store(path: Path) -> TxStore:
    """Charge un wallet.json existant. Retourne un Wallet vide si le fichier
    n'existe pas encore (premier import)."""
    tx_store = TxStore()

    if not path.exists():
        return tx_store

    data = json.loads(path.read_text(encoding="utf-8"))
    assets_meta = data.get("assets", {})

    for tx_data in data.get("transactions", []):
        tx = _transaction_from_dict(tx_data,tx_store, assets_meta)
        tx_store.transactions.append(tx)
        if tx.external_id is not None:
            tx_store._known_external_ids.add(tx.external_id)

    return tx_store


def save_wallet(tx_store: TxStore, path: Path) -> None:
    """Réécrit le wallet.json en entier (pas d'append) -- garantit un
    fichier toujours cohérent avec l'état en mémoire."""
    assets_out = {
    symbol: {
        "name": asset.name,
        "kind": asset.kind.value,
        "ref_currency": asset.ref_currency,
        "identifiers": asdict(asset.identifiers),
    }
    for symbol, asset in tx_store.assets.items()
    }

    transactions_out = [
        _transaction_to_dict(tx) for tx in tx_store.transactions
    ]
    transactions_out.sort(key=lambda d: d["time"])  # ordre chronologique stable -> diffs git lisibles

    payload = {
        "version": TX_STORE_VERSION,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "assets": assets_out,
        "transactions": transactions_out,
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Alias de compatibilité
# ---------------------------------------------------------------------------
# cli.py, ledger/positions.py et ledger/cost_basis.py importent `Wallet` et
# `load_wallet` (nommage pré-renommage), alors que ce module définit `TxStore`
# et `load_tx_store` (nommage post-renommage vers serialized_tx.json). Sans
# ces alias, TOUT le package échoue à l'import (ImportError). Cf. le message
# ci-dessous pour le détail -- à corriger dans le vrai code plutôt que de
# garder cet alias indéfiniment.
Wallet = TxStore
load_wallet = load_tx_store
