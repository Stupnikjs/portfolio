from datetime import datetime, timezone

import pytest

from src.registry import AssetRegistry
from src.schema import AssetIdentifiers, AssetKind, Platform, Transaction, TransactionKind


def make_tx(
    registry: AssetRegistry,
    symbol: str,
    kind: TransactionKind,
    quantity: float,
    value_eur: float,
    time: datetime,
    external_id: str | None = None,
    asset_kind: AssetKind = AssetKind.CRYPTO,
    ref_currency: str = "USD",
    price: float | None = None,
    amount: float | None = None,
    quote_currency: str | None = None,
    remark: str | None = None,
    source_file: str = "test",
    account_label: str = "Spot",
    platform: Platform = Platform.BINANCE,
) -> Transaction:
    """Construit une Transaction de test et enregistre son actif dans `registry`."""
    asset_id = registry.find_or_create(symbol, symbol, asset_kind, ref_currency, AssetIdentifiers())
    return Transaction(
        platform=platform,
        account_label=account_label,
        kind=kind,
        asset_id=asset_id,
        quantity=quantity,
        price=price,
        value_eur=value_eur,
        amount=amount,
        quote_currency=quote_currency,
        time=time,
        external_id=external_id,
        remark=remark,
        source_file=source_file,
    )


@pytest.fixture
def registry() -> AssetRegistry:
    return AssetRegistry()


@pytest.fixture
def t0() -> datetime:
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
