# src/parse/manual.py
"""Parseur pour les transactions manuelles (data/raw/manual.json) --
comble les trous non couverts par les exports automatisés (ex: on-chain
non tracé). Remplacé en bloc à chaque run -- voir TxStore.replace_platform.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

from .binance import _synthetic_id
from ..schema import Asset, AssetIdentifiers, AssetKind, Platform, Transaction, TransactionKind


def _parse_time(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def parse_manual(path: Path) -> list[Transaction]:
    if not path.exists():
        return []

    entries = json.loads(path.read_text(encoding="utf-8"))
    out = []

    for entry in entries:
        symbol = entry["asset"]
        asset = Asset(symbol=symbol, name=symbol, kind=AssetKind.CRYPTO,
                      ref_currency="EUR", identifiers=AssetIdentifiers())
        raw_id = entry.get("id") or _synthetic_id("manual-auto", json.dumps(entry, sort_keys=True))

        out.append(Transaction(
            platform=Platform.MANUAL,
            account_label=entry.get("account_label", "Manuel"),
            kind=TransactionKind(entry["kind"]),
            asset=asset,
            quantity=float(entry["quantity"]),
            price=entry.get("price"),
            value_eur=float(entry["value_eur"]),
            amount=entry.get("amount"),
            quote_currency=entry.get("quote_currency"),
            time=_parse_time(entry["time"]),
            external_id=f"manual-{raw_id}",
            remark=entry.get("remark"),
            source_file=str(path),
        ))

    return out