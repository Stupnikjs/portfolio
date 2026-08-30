"""Types de base, équivalent Python du crate pf-core.

Le crate `pf-core` n'était PAS inclus dans l'archive fournie (seul `pf-extract`,
c.-à-d. binance.rs/xtb.rs, y était). Les types ci-dessous sont reconstruits à
partir de ce qui est utilisé dans ces deux fichiers. Si ta vraie définition
Rust de `AssetIdentifiers` ou `Transaction` a d'autres champs, ajuste ici.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    BINANCE = "Binance"
    XTB = "Xtb"


class TransactionKind(str, Enum):
    BUY = "Buy"
    SELL = "Sell"
    FEE = "Fee"


class AssetKind(str, Enum):
    CASH = "Cash"
    CRYPTO = "Crypto"
    STOCK = "Stock"


@dataclass
class AssetIdentifiers:
    """Identifiants externes optionnels d'un actif (ISIN, ticker...).
    `AssetIdentifiers::default()` en Rust ne montre pas les champs réels --
    complète cette classe si ta version en a d'autres (ISIN, CUSIP, etc.)."""

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
    amount: Optional[float]
    quote_currency: Optional[str]
    time: datetime
    external_id: Optional[str]
    remark: Optional[str]
    source_file: str