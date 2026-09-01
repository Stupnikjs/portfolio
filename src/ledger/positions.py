"""Reconstruction des positions (quantités détenues) à partir du log de
transactions du wallet -- pattern event-sourcing : le wallet.json ne
stocke jamais de solde calculé, seulement les transactions brutes.
`holdings_at` est la seule source de vérité pour "combien j'ai de X à
telle date".
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from ..schema import TransactionKind
from ..store.serialize import TxStore

# Sens du mouvement de quantité pour l'actif principal de la transaction,
# selon son kind. BUY/DEPOSIT augmentent la position, SELL/WITHDRAW/FEE
# la diminuent.
_SIGN: Dict[TransactionKind, int] = {
    TransactionKind.BUY: +1,
    TransactionKind.DEPOSITE: +1,
    TransactionKind.SELL: -1,
    TransactionKind.WITHDRAW: -1,
    TransactionKind.FEE: -1,
}


def holdings_at(tx_store: TxStore, at: Optional[datetime] = None) -> Dict[str, float]:
    """Quantité détenue par symbole à la date `at` (incluse).

    `at=None` signifie "maintenant" au sens de "toutes les transactions
    connues" -- pratique pour un snapshot de l'état courant.

    Les quantités quasi nulles issues d'arrondis flottants (< 1e-12) sont
    ramenées à zéro pour éviter les faux positifs de type "je détiens
    encore 0.0000000000003 BTC".
    """
    holdings: Dict[str, float] = {}

    for tx in sorted(tx_store.transactions, key=lambda t: t.time):
        if at is not None and tx.time > at:
            break

        symbol = tx_store.registry.get_asset(tx.asset_id).symbol
        sign = _SIGN.get(tx.kind)
        if sign is None:
            raise ValueError(f"TransactionKind non géré dans holdings_at: {tx.kind}")

        holdings[symbol] = holdings.get(symbol, 0.0) + sign * tx.quantity

    for symbol, qty in list(holdings.items()):
        if abs(qty) < 1e-12:
            holdings[symbol] = 0.0

    return holdings


def non_zero_holdings_at(tx_store: TxStore, at: Optional[datetime] = None) -> Dict[str, float]:
    """Comme `holdings_at`, mais filtre les actifs à quantité nulle --
    pratique pour n'afficher que ce qui est réellement détenu."""
    return {symbol: qty for symbol, qty in holdings_at(tx_store, at).items() if qty != 0.0}
