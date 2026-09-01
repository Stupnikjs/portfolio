from datetime import timedelta

import pytest

from src.ledger.cost_basis import compute_fifo
from src.schema import TransactionKind
from src.store.serialize import TxStore

from tests.conftest import make_tx


def test_fifo_matches_single_buy_then_sell(registry, t0):
    store = TxStore()
    txs = [
        make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 10000.0, t0, external_id="e1"),
        make_tx(registry, "BTC", TransactionKind.SELL, 1.0, 15000.0, t0 + timedelta(days=1), external_id="e2"),
    ]
    store.add_transactions(txs, registry)
    result = compute_fifo(store)

    assert result.open_quantity("BTC") == 0.0
    assert len(result.realized_gains) == 1
    gain = result.realized_gains[0]
    assert gain.cost_eur == pytest.approx(10000.0)
    assert gain.proceeds_eur == pytest.approx(15000.0)
    assert gain.pnl_eur == pytest.approx(5000.0)
    assert not gain.incomplete


def test_fifo_consumes_oldest_lot_first_across_two_buys(registry, t0):
    """Achat 1 BTC @1000, achat 1 BTC @3000, vente de 1 BTC : le coût doit
    venir du PREMIER lot (1000), pas d'une moyenne (2000) ni du dernier
    (3000) -- c'est la différence concrète FIFO vs coût moyen pondéré."""
    store = TxStore()
    txs = [
        make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 1000.0, t0, external_id="e1"),
        make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 3000.0, t0 + timedelta(days=1), external_id="e2"),
        make_tx(registry, "BTC", TransactionKind.SELL, 1.0, 5000.0, t0 + timedelta(days=2), external_id="e3"),
    ]
    store.add_transactions(txs, registry)
    result = compute_fifo(store)

    gain = result.realized_gains[0]
    assert gain.cost_eur == pytest.approx(1000.0)
    assert gain.pnl_eur == pytest.approx(4000.0)
    assert result.open_quantity("BTC") == pytest.approx(1.0)
    assert result.average_cost("BTC") == pytest.approx(3000.0)


def test_fifo_sell_spanning_multiple_lots(registry, t0):
    store = TxStore()
    txs = [
        make_tx(registry, "BTC", TransactionKind.BUY, 0.5, 500.0, t0, external_id="e1"),
        make_tx(registry, "BTC", TransactionKind.BUY, 0.5, 1000.0, t0 + timedelta(days=1), external_id="e2"),
        make_tx(registry, "BTC", TransactionKind.SELL, 0.8, 2000.0, t0 + timedelta(days=2), external_id="e3"),
    ]
    store.add_transactions(txs, registry)
    result = compute_fifo(store)

    gain = result.realized_gains[0]
    # 0.5 @ (500/0.5=1000/u) + 0.3 @ (1000/0.5=2000/u) = 500 + 600 = 1100
    assert gain.cost_eur == pytest.approx(1100.0)
    assert len(gain.lots_consumed) == 2
    assert result.open_quantity("BTC") == pytest.approx(0.2)


def test_fifo_sell_exceeding_known_lots_marks_incomplete(registry, t0):
    """Vente supérieure aux lots connus (dépôt/transfert non tracé) : le
    reliquat est coûté à 0 et `incomplete=True` plutôt que de planter ou
    de fausser silencieusement le P&L."""
    store = TxStore()
    txs = [
        make_tx(registry, "BTC", TransactionKind.BUY, 0.5, 500.0, t0, external_id="e1"),
        make_tx(registry, "BTC", TransactionKind.SELL, 1.0, 3000.0, t0 + timedelta(days=1), external_id="e2"),
    ]
    store.add_transactions(txs, registry)
    result = compute_fifo(store)

    gain = result.realized_gains[0]
    assert gain.incomplete is True
    assert gain.cost_eur == pytest.approx(500.0)  # seul le lot connu est coûté
    assert gain.pnl_eur == pytest.approx(2500.0)  # donc P&L surestimé de 500*prix_manquant


def test_fifo_fees_are_accumulated_separately_and_not_in_pnl(registry, t0):
    store = TxStore()
    txs = [
        make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 1000.0, t0, external_id="e1"),
        make_tx(registry, "BTC", TransactionKind.FEE, 0.001, 5.0, t0, external_id=None),
        make_tx(registry, "BTC", TransactionKind.SELL, 1.0, 2000.0, t0 + timedelta(days=1), external_id="e2"),
    ]
    store.add_transactions(txs, registry)
    result = compute_fifo(store)

    assert result.total_fees("BTC") == pytest.approx(5.0)
    assert result.total_fees() == pytest.approx(5.0)
    # Le FEE ne doit pas venir polluer le pnl_eur du realized_gain BUY/SELL.
    assert result.total_realized_pnl("BTC") == pytest.approx(1000.0)


def test_fifo_respects_as_of_date(registry, t0):
    store = TxStore()
    txs = [
        make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 1000.0, t0, external_id="e1"),
        make_tx(registry, "BTC", TransactionKind.SELL, 1.0, 5000.0, t0 + timedelta(days=30), external_id="e2"),
    ]
    store.add_transactions(txs, registry)

    result_before_sell = compute_fifo(store, at=t0 + timedelta(days=1))
    assert result_before_sell.open_quantity("BTC") == pytest.approx(1.0)
    assert result_before_sell.realized_gains == []

    result_after_sell = compute_fifo(store, at=t0 + timedelta(days=31))
    assert result_after_sell.open_quantity("BTC") == 0.0
    assert len(result_after_sell.realized_gains) == 1


def test_average_cost_is_none_when_nothing_held(registry, t0):
    store = TxStore()
    result = compute_fifo(store)
    assert result.average_cost("BTC") is None
    assert result.open_quantity("BTC") == 0.0
    assert result.open_cost_basis("BTC") == 0.0


def test_compute_fifo_raises_on_unhandled_transaction_kind(registry, t0, monkeypatch):
    """Si un futur TransactionKind est ajouté au schéma sans être branché
    dans compute_fifo, on veut un échec explicite plutôt qu'un P&L
    silencieusement incomplet."""
    import enum

    store = TxStore()
    tx = make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0, external_id="e1")
    store.add_transactions([tx], registry)
    # On force un kind non géré directement sur l'objet en mémoire.
    store.transactions[0].kind = "SomethingElse"  # type: ignore[assignment]

    with pytest.raises(ValueError, match="non géré"):
        compute_fifo(store)


def test_unit_value_eur_rejects_non_positive_quantity(registry, t0):
    """`_unit_value_eur` doit lever plutôt que produire une division par
    zéro silencieuse ou un coût unitaire négatif absurde."""
    from src.ledger.cost_basis import _unit_value_eur

    with pytest.raises(ValueError):
        _unit_value_eur(0.0, 100.0)
    with pytest.raises(ValueError):
        _unit_value_eur(-1.0, 100.0)
