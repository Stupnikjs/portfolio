"""Calcul de la valorisation du portefeuille à une date donnée.
Combine les positions (quantités) avec les prix de marché historiques.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..store.serialize import TxStore
from .positions import holdings_at
from ..market.prices import historical_price_eur
from ..schema import AssetKind

def portfolio_snapshot_at(tx_store: TxStore, at: Optional[datetime] = None) -> dict:
    if at is None:
        at = datetime.now(timezone.utc)
    elif at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)

    holdings = holdings_at(tx_store, at)
    total_value_eur = 0.0
    details = []

    for symbol, quantity in holdings.items():
        if abs(quantity) < 1e-12:
            continue

        asset = tx_store.assets.get(symbol)
        ticker = asset.identifiers.ticker if asset else None
        kind = asset.kind if asset else AssetKind.CRYPTO  # Fallback défensif

        price_eur = 0.0
        try:
            # On passe le kind et le ticker
            price_eur = historical_price_eur(symbol, at, kind, ticker)
        except Exception as e:
            print(f"  [WARN] Impossible d'évaluer {symbol} au {at.strftime('%Y-%m-%d')}: {e}")
            
        value_eur = quantity * price_eur
        total_value_eur += value_eur

        details.append({
            "symbol": symbol,
            "quantity": quantity,
            "price_eur": price_eur,
            "value_eur": value_eur,
            "kind": kind.value if hasattr(kind, 'value') else str(kind),
            "ticker": ticker
        })

    details.sort(key=lambda x: x["value_eur"], reverse=True)

    return {
        "date": at.strftime("%Y-%m-%d"),
        "total_value_eur": total_value_eur,
        "assets": details
    }