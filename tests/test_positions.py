from datetime import timedelta

import pytest

from src.ledger.positions import holdings_at, non_zero_holdings_at
from src.schema import TransactionKind
from src.store.serialize import TxStore

from tests.conftest import make_tx


def test_holdings_at_accumulates_buys(registry, t0):
    store = TxStore()
    tx1 = make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0, external_id="e1")
    tx2 = make_tx(registry, "BTC", TransactionKind.BUY, 0.5, 50.0, t0 + timedelta(days=1), external_id="e2")
    store.add_transactions([tx1, tx2], registry)

    assert holdings_at(store) == {"BTC": 1.5}


def test_holdings_at_subtracts_sells_and_withdrawals(registry, t0):
    store = TxStore()
    txs = [
        make_tx(registry, "BTC", TransactionKind.BUY, 2.0, 200.0, t0, external_id="e1"),
        make_tx(registry, "BTC", TransactionKind.SELL, 0.5, 60.0, t0 + timedelta(days=1), external_id="e2"),
        make_tx(registry, "BTC", TransactionKind.WITHDRAW, 0.5, 60.0, t0 + timedelta(days=2), external_id="e3"),
    ]
    store.add_transactions(txs, registry)

    assert holdings_at(store)["BTC"] == pytest.approx(1.0)


def test_holdings_at_respects_as_of_date(registry, t0):
    store = TxStore()
    txs = [
        make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0, external_id="e1"),
        make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0 + timedelta(days=10), external_id="e2"),
    ]
    store.add_transactions(txs, registry)

    assert holdings_at(store, at=t0) == {"BTC": 1.0}
    assert holdings_at(store, at=t0 + timedelta(days=10)) == {"BTC": 2.0}


def test_holdings_at_snaps_floating_point_dust_to_zero(registry, t0):
    store = TxStore()
    txs = [
        make_tx(registry, "BTC", TransactionKind.BUY, 0.1, 10.0, t0, external_id="e1"),
        make_tx(registry, "BTC", TransactionKind.SELL, 0.1, 10.0, t0 + timedelta(days=1), external_id="e2"),
    ]
    store.add_transactions(txs, registry)

    assert holdings_at(store)["BTC"] == 0.0


def test_non_zero_holdings_at_filters_zero_balances(registry, t0):
    store = TxStore()
    txs = [
        make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0, external_id="e1"),
        make_tx(registry, "BTC", TransactionKind.SELL, 1.0, 100.0, t0 + timedelta(days=1), external_id="e2"),
        make_tx(registry, "ETH", TransactionKind.BUY, 1.0, 100.0, t0, external_id="e3"),
    ]
    store.add_transactions(txs, registry)

    result = non_zero_holdings_at(store)
    assert result == {"ETH": 1.0}
    assert "BTC" not in result


def test_holdings_at_fee_reduces_holdings_of_fee_asset():
    """FEE est marqué comme diminuant la position de l'actif du frais
    (`_SIGN[FEE] = -1`) -- vérifie explicitement ce cas, car c'est
    facilement le kind le plus surprenant du mapping."""
    from src.registry import AssetRegistry
    registry = AssetRegistry()
    from datetime import datetime, timezone
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store = TxStore()
    txs = [
        make_tx(registry, "BNB", TransactionKind.BUY, 1.0, 200.0, t0, external_id="e1"),
        make_tx(registry, "BNB", TransactionKind.FEE, 0.01, 2.0, t0, external_id=None),
    ]
    store.add_transactions(txs, registry)
    assert holdings_at(store)["BNB"] == pytest.approx(0.99)
