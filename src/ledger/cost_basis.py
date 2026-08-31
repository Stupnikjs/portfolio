"""
Calcul du cost basis (prix de revient) par méthode FIFO, et du P&L réalisé
à la vente -- construit sur la même passe unique triée par temps que
`positions.py`.

FIFO plutôt que coût moyen pondéré : c'est la méthode retenue par défaut
par l'administration fiscale française pour les cessions de valeurs
mobilières, donc partir directement sur FIFO évite d'avoir à tout refaire
au moment d'une déclaration.

Le coût/produit de chaque transaction est dérivé de `value_eur` (marqué
immutable dans schema.py, donc la valeur EUR faisant autorité) plutôt que
de `quantity * price` : `price` est optionnel et parfois exprimé dans la
devise locale de l'actif plutôt qu'en EUR (cas XTB), donc le recalculer
soi-même serait faux dans ce cas.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Dict, List, Optional

from ..schema import TransactionKind
from ..store.serialize import Wallet


def _unit_value_eur(quantity: float, value_eur: float) -> float:
    """Valeur EUR par unité, dérivée de `value_eur` (champ immutable qui
    fait autorité) plutôt que de `tx.price` (optionnel, parfois en devise
    locale plutôt qu'en EUR -- voir XtbClosedPosition/XtbOpenPosition)."""
    if quantity <= 0:
        raise ValueError(f"quantity doit être positive, reçu {quantity}")
    return value_eur / quantity


@dataclass
class Lot:
    """Un lot FIFO : une tranche de quantité acquise à un prix donné."""
    quantity: float
    unit_cost_eur: float
    acquired_at: datetime
    external_id: Optional[str] = None


@dataclass
class RealizedGain:
    """Résultat d'une vente rapprochée avec un ou plusieurs lots FIFO."""
    symbol: str
    sell_time: datetime
    quantity: float
    proceeds_eur: float
    cost_eur: float
    pnl_eur: float
    external_id: Optional[str] = None
    lots_consumed: List[Lot] = field(default_factory=list)
    incomplete: bool = False  # True si la vente dépasse les lots connus


@dataclass
class CostBasisResult:
    """Sortie complète du calcul FIFO pour un wallet."""
    open_lots: Dict[str, List[Lot]]       # symbol -> lots restants, ordre FIFO
    realized_gains: List[RealizedGain]    # historique des ventes rapprochées
    fees_eur_by_symbol: Dict[str, float]  # frais cumulés par actif

    def open_quantity(self, symbol: str) -> float:
        return sum(lot.quantity for lot in self.open_lots.get(symbol, []))

    def open_cost_basis(self, symbol: str) -> float:
        """Coût de revient total des lots encore ouverts pour `symbol`."""
        return sum(lot.quantity * lot.unit_cost_eur for lot in self.open_lots.get(symbol, []))

    def average_cost(self, symbol: str) -> Optional[float]:
        """Prix de revient moyen par unité sur les lots ouverts (None si rien détenu)."""
        qty = self.open_quantity(symbol)
        if qty <= 0:
            return None
        return self.open_cost_basis(symbol) / qty

    def total_realized_pnl(self, symbol: Optional[str] = None) -> float:
        gains = self.realized_gains if symbol is None else [g for g in self.realized_gains if g.symbol == symbol]
        return sum(g.pnl_eur for g in gains)

    def total_fees(self, symbol: Optional[str] = None) -> float:
        if symbol is not None:
            return self.fees_eur_by_symbol.get(symbol, 0.0)
        return sum(self.fees_eur_by_symbol.values())


def compute_fifo(wallet: Wallet, at: Optional[datetime] = None) -> CostBasisResult:
    """Rejoue les transactions du wallet dans l'ordre chronologique et
    applique la méthode FIFO : chaque SELL/WITHDRAW consomme les lots
    BUY/DEPOSITE les plus anciens en premier.

    `at=None` -- comme pour `holdings_at` -- rejoue toutes les transactions
    connues. Passer une date permet un calcul "à l'époque" (utile pour une
    déclaration fiscale sur une année passée, par exemple).

    Les FEE ne sont pas rattachés à un lot précis : le schéma actuel ne
    permet pas de distinguer de façon fiable si un frais porte sur l'achat
    ou sur la vente. Ils sont donc accumulés séparément par actif
    (`fees_eur_by_symbol`) -- à soustraire toi-même du P&L si tu veux un
    résultat net de frais.

    Si une vente dépasse la quantité connue en lots ouverts (transfert
    entrant non tracé, données historiques incomplètes...), le reliquat
    est valorisé à un coût de 0 et le `RealizedGain` correspondant est
    marqué `incomplete=True` -- son `pnl_eur` est donc surestimé d'autant.
    """
    lots: Dict[str, Deque[Lot]] = {}
    realized: List[RealizedGain] = []
    fees: Dict[str, float] = {}

    transactions = sorted(wallet.transactions, key=lambda t: t.time)

    for tx in transactions:
        if at is not None and tx.time > at:
            break

        symbol = wallet.registry.get_asset(tx.asset_id).symbol

        if tx.kind in (TransactionKind.BUY, TransactionKind.DEPOSITE):
            queue = lots.setdefault(symbol, deque())
            queue.append(Lot(
                quantity=tx.quantity,
                unit_cost_eur=_unit_value_eur(tx.quantity, tx.value_eur),
                acquired_at=tx.time,
                external_id=tx.external_id,
            ))

        elif tx.kind in (TransactionKind.SELL, TransactionKind.WITHDRAW):
            queue = lots.setdefault(symbol, deque())
            remaining = tx.quantity
            consumed: List[Lot] = []
            cost_eur = 0.0
            incomplete = False

            while remaining > 1e-12 and queue:
                lot = queue[0]
                take = min(lot.quantity, remaining)

                cost_eur += take * lot.unit_cost_eur
                consumed.append(Lot(
                    quantity=take, unit_cost_eur=lot.unit_cost_eur,
                    acquired_at=lot.acquired_at, external_id=lot.external_id,
                ))

                lot.quantity -= take
                remaining -= take
                if lot.quantity <= 1e-12:
                    queue.popleft()

            if remaining > 1e-12:
                # Pas de lot connu pour couvrir le reliquat : coût inconnu,
                # traité comme 0 -- signalé via `incomplete` plutôt que
                # silencieusement absorbé dans le P&L.
                consumed.append(Lot(quantity=remaining, unit_cost_eur=0.0, acquired_at=tx.time))
                incomplete = True

            proceeds_eur = tx.value_eur
            realized.append(RealizedGain(
                symbol=symbol,
                sell_time=tx.time,
                quantity=tx.quantity,
                proceeds_eur=proceeds_eur,
                cost_eur=cost_eur,
                pnl_eur=proceeds_eur - cost_eur,
                external_id=tx.external_id,
                lots_consumed=consumed,
                incomplete=incomplete,
            ))

        elif tx.kind == TransactionKind.FEE:
            fees[symbol] = fees.get(symbol, 0.0) + (tx.value_eur or 0.0)

        else:
            raise ValueError(f"TransactionKind non géré dans compute_fifo: {tx.kind}")

    open_lots = {symbol: list(queue) for symbol, queue in lots.items() if queue}
    return CostBasisResult(open_lots=open_lots, realized_gains=realized, fees_eur_by_symbol=fees)
