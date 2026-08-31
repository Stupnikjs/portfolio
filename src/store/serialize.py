
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

from ..registry import AssetRegistry
from ..schema import (
    AssetIdentifiers,
    AssetKind,
    Platform,
    Transaction,
    TransactionKind,
)

TX_STORE_VERSION = 1


# ---------------------------------------------------------------------------
# Sérialisation Transaction <-> dict (par symbole)
# ---------------------------------------------------------------------------

def _transaction_to_dict(tx: Transaction, registry: AssetRegistry) -> dict:
    asset = registry.get_asset(tx.asset_id)
    return {
        "platform": tx.platform.value,
        "account_label": tx.account_label,
        "kind": tx.kind.value,
        "asset": asset.symbol,
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


def _transaction_from_dict(data: dict, registry: AssetRegistry, assets_meta: Dict[str, dict]) -> Transaction:
    symbol = data["asset"]
    meta = assets_meta[symbol]
    asset_id = registry.find_or_create(
        symbol,
        meta["name"],
        AssetKind(meta["kind"]),
        meta["ref_currency"],
        AssetIdentifiers(**meta["identifiers"]),
    )
    return Transaction(
        platform=Platform(data["platform"]),
        account_label=data["account_label"],
        kind=TransactionKind(data["kind"]),
        asset_id=asset_id,
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
    """État persistant du portefeuille : registre d'actifs (keyed par
    symbole en interne) + log de transactions, source de vérité unique.

    Ne jamais stocker de positions/soldes calculés ici -- ils se
    reconstruisent à partir du log de transactions (voir portfolio/).
    """

    def __init__(self) -> None:
        self.registry = AssetRegistry()
        self.transactions: List[Transaction] = []
        self._known_external_ids: Set[str] = set()

    def add_transactions(self, new_transactions: List[Transaction], source_registry: AssetRegistry) -> int:
        """Fusionne des transactions fraîchement parsées dans le wallet.

        `source_registry` est l'AssetRegistry utilisé par les parsers pour
        produire `new_transactions` -- ses asset_id sont locaux à ce run et
        ne correspondent pas forcément à ceux du wallet. On les retraduit
        via le symbole.

        Les doublons (même external_id déjà connu) sont silencieusement
        ignorés. Retourne le nombre de transactions effectivement ajoutées.
        """
        added = 0
        for tx in new_transactions:
            if tx.external_id is not None and tx.external_id in self._known_external_ids:
                continue

            source_asset = source_registry.get_asset(tx.asset_id)
            local_asset_id = self.registry.find_or_create(
                source_asset.symbol,
                source_asset.name,
                source_asset.kind,
                source_asset.ref_currency,
                source_asset.identifiers,
            )

            self.transactions.append(Transaction(
                platform=tx.platform,
                account_label=tx.account_label,
                kind=tx.kind,
                asset_id=local_asset_id,
                quantity=tx.quantity,
                price=tx.price,
                value_eur=tx.value_eur,
                amount=tx.amount,
                quote_currency=tx.quote_currency,
                time=tx.time,
                external_id=tx.external_id,
                remark=tx.remark,
                source_file=tx.source_file,
            ))
            if tx.external_id is not None:
                self._known_external_ids.add(tx.external_id)
            added += 1

        return added


# ---------------------------------------------------------------------------
# Chargement / sauvegarde JSON
# ---------------------------------------------------------------------------

def load_tx_store(path: Path) -> TxStore:
    """Charge un wallet.json existant. Retourne un Wallet vide si le fichier
    n'existe pas encore (premier import)."""
    wallet = TxStore()

    if not path.exists():
        return wallet

    data = json.loads(path.read_text(encoding="utf-8"))
    assets_meta = data.get("assets", {})

    for tx_data in data.get("transactions", []):
        tx = _transaction_from_dict(tx_data, wallet.registry, assets_meta)
        wallet.transactions.append(tx)
        if tx.external_id is not None:
            wallet._known_external_ids.add(tx.external_id)

    return wallet


def save_wallet(tx_store: TxStore, path: Path) -> None:
    """Réécrit le wallet.json en entier (pas d'append) -- garantit un
    fichier toujours cohérent avec l'état en mémoire."""
    assets_out = {
        asset.symbol: {
            "name": asset.name,
            "kind": asset.kind.value,
            "ref_currency": asset.ref_currency,
            "identifiers": asdict(asset.identifiers),
        }
        for asset in tx_store.registry.get_all_assets()
    }

    transactions_out = [
        _transaction_to_dict(tx, tx_store.registry) for tx in tx_store.transactions
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