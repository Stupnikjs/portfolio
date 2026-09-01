"""Types de base, équivalent Python du crate pf-core.

Le crate `pf-core` n'était PAS inclus dans l'archive fournie (seul `pf-extract`,
c.-à-d. binance.rs/xtb.rs, y était). Les types ci-dessous sont reconstruits à
partir de ce qui est utilisé dans ces deux fichiers. Si ta vraie définition
Rust de `AssetIdentifiers` ou `Transaction` a d'autres champs, ajuste ici.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    BINANCE = "Binance"
    XTB = "Xtb"
    MANUAL  = "Manual"


class TransactionKind(str, Enum):
    BUY = "Buy"
    SELL = "Sell"
    FEE = "Fee"
    DEPOSITE = "Deposit"
    WITHDRAW = "Withdraw"


class AssetKind(str, Enum):
    CASH = "Cash"
    CRYPTO = "Crypto"
    STOCK = "Stock"


@dataclass
class AssetIdentifiers:
    """Identifiants externes optionnels d'un actif (ISIN, ticker...)."""

    isin: Optional[str] = None
    ticker: Optional[str] = None


@dataclass
class Asset:
    id: int
    symbol: str
    name: str
    kind: AssetKind
    ref_currency: str
    identifiers: AssetIdentifiers


@dataclass
class Transaction:
    platform: Platform
    account_label: str
    kind: TransactionKind
    asset_id: int
    quantity: float
    price: Optional[float]
    value_eur: float  # immutable
    amount: Optional[float]
    quote_currency: Optional[str]
    time: datetime
    external_id: Optional[str]
    remark: Optional[str]
    source_file: str


def _asset_id(symbol: str, kind: AssetKind, ref_currency: str) -> int:
    """ID stable : le même triplet (symbol, kind, ref_currency) donne
    toujours le même id, peu importe l'ordre de parsing ou le run."""
    digest = hashlib.sha256(f"{kind.value}|{ref_currency}|{symbol}".encode()).hexdigest()
    return int(digest[:15], 16)  # tient dans un int 64 bits signé
