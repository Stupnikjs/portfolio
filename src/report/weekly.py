"""
report/weekly.py

Rapport hebdomadaire de portefeuille : valorisation et variation sur 7
jours, par actif et par classe d'actif (Cash/Crypto/Stock), transactions
de la semaine, P&L réalisé de la semaine.

Principe : les chiffres sont TOUJOURS calculés par le ledger existant
(portfolio_snapshot_at, compute_fifo) -- ce module ne fait qu'agréger et
mettre en forme. La fonction `narrate()` en bas de fichier est un point
d'extension optionnel pour brancher un LLM qui rédigerait un résumé en
prose à partir de ces chiffres déjà calculés -- le LLM ne recalcule
jamais rien, il met en mots ce qui existe déjà.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional

from ..ledger.cost_basis import compute_fifo
from ..ledger.portfolio import portfolio_snapshot_at
from ..schema import AssetKind
from ..store.serialize import TxStore


@dataclass
class AssetWeeklyLine:
    """Une ligne du rapport : l'évolution d'un actif sur la période."""
    symbol: str
    kind: AssetKind
    quantity_now: float
    quantity_week_ago: float
    value_eur_now: float
    value_eur_week_ago: float
    realized_pnl_eur: float
    fees_eur: float
    tx_count: int

    @property
    def value_delta_eur(self) -> float:
        return self.value_eur_now - self.value_eur_week_ago

    @property
    def value_delta_pct(self) -> Optional[float]:
        """None si l'actif n'était pas détenu il y a 7 jours (pas de base
        pour un pourcentage -- afficher '+X EUR (nouveau)' plutôt qu'un
        pourcentage infini ou trompeur)."""
        if self.value_eur_week_ago <= 1e-9:
            return None
        return (self.value_delta_eur / self.value_eur_week_ago) * 100


@dataclass
class WeeklyReport:
    period_start: datetime
    period_end: datetime
    total_value_now: float
    total_value_week_ago: float
    lines: List[AssetWeeklyLine]

    @property
    def total_delta_eur(self) -> float:
        return self.total_value_now - self.total_value_week_ago

    @property
    def total_delta_pct(self) -> Optional[float]:
        if self.total_value_week_ago <= 1e-9:
            return None
        return (self.total_delta_eur / self.total_value_week_ago) * 100

    def lines_by_kind(self, kind: AssetKind) -> List[AssetWeeklyLine]:
        return [l for l in self.lines if l.kind == kind]

    def total_by_kind(self, kind: AssetKind) -> float:
        return sum(l.value_eur_now for l in self.lines_by_kind(kind))


def build_weekly_report(tx_store: TxStore, as_of: Optional[datetime] = None) -> WeeklyReport:
    """Construit le rapport pour les 7 jours se terminant à `as_of`
    (défaut : maintenant). Compare deux snapshots de portefeuille --
    coûte donc 2x le nombre d'appels de prix qu'un snapshot seul, c'est
    le cache de prix (voir market/prices.py) qui absorbe ce coût sur les
    runs répétés."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    elif as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)

    period_start = as_of - timedelta(days=7)

    snapshot_now = portfolio_snapshot_at(tx_store, as_of)
    snapshot_before = portfolio_snapshot_at(tx_store, period_start)

    now_by_symbol = {a["symbol"]: a for a in snapshot_now["assets"]}
    before_by_symbol = {a["symbol"]: a for a in snapshot_before["assets"]}

    cb = compute_fifo(tx_store, at=as_of)

    week_tx = [tx for tx in tx_store.transactions if period_start <= tx.time <= as_of]
    tx_count_by_symbol: Dict[str, int] = {}
    for tx in week_tx:
        tx_count_by_symbol[tx.asset.symbol] = tx_count_by_symbol.get(tx.asset.symbol, 0) + 1

    realized_this_week: Dict[str, float] = {}
    for gain in cb.realized_gains:
        if period_start <= gain.sell_time <= as_of:
            realized_this_week[gain.symbol] = realized_this_week.get(gain.symbol, 0.0) + gain.pnl_eur

    symbols = set(now_by_symbol) | set(before_by_symbol) | set(tx_count_by_symbol)

    lines: List[AssetWeeklyLine] = []
    for symbol in symbols:
        now_entry = now_by_symbol.get(symbol)
        before_entry = before_by_symbol.get(symbol)

        qty_now = now_entry["quantity"] if now_entry else 0.0
        qty_before = before_entry["quantity"] if before_entry else 0.0
        val_now = now_entry["value_eur"] if now_entry else 0.0
        val_before = before_entry["value_eur"] if before_entry else 0.0

        asset_meta = tx_store.assets.get(symbol)
        kind = asset_meta.kind if asset_meta else AssetKind.CRYPTO

        # Rien à raconter : ni détenu maintenant, ni il y a 7 jours, ni de
        # transaction dans la période -- on n'encombre pas le rapport.
        if abs(qty_now) < 1e-12 and abs(qty_before) < 1e-12 and tx_count_by_symbol.get(symbol, 0) == 0:
            continue

        lines.append(AssetWeeklyLine(
            symbol=symbol,
            kind=kind,
            quantity_now=qty_now,
            quantity_week_ago=qty_before,
            value_eur_now=val_now,
            value_eur_week_ago=val_before,
            realized_pnl_eur=realized_this_week.get(symbol, 0.0),
            fees_eur=cb.total_fees(symbol),
            tx_count=tx_count_by_symbol.get(symbol, 0),
        ))

    lines.sort(key=lambda l: l.value_eur_now, reverse=True)

    return WeeklyReport(
        period_start=period_start,
        period_end=as_of,
        total_value_now=snapshot_now["total_value_eur"],
        total_value_week_ago=snapshot_before["total_value_eur"],
        lines=lines,
    )


def render_markdown(report: WeeklyReport) -> str:
    """Rendu Markdown déterministe -- même rapport = même texte, tous les
    chiffres tracables jusqu'au ledger."""
    out = []
    out.append(f"# Rapport hebdomadaire — {report.period_start:%d/%m/%Y} → {report.period_end:%d/%m/%Y}\n")

    sign = "+" if report.total_delta_eur >= 0 else ""
    pct = f" ({sign}{report.total_delta_pct:.1f}%)" if report.total_delta_pct is not None else " (nouveau)"
    out.append(
        f"**Valeur totale : {report.total_value_now:,.2f} EUR** "
        f"({sign}{report.total_delta_eur:,.2f} EUR{pct} sur 7 jours)\n"
    )

    if not report.lines:
        out.append("\nAucun mouvement ni position sur la période.\n")
        return "\n".join(out)

    for kind in AssetKind:
        kind_lines = report.lines_by_kind(kind)
        if not kind_lines:
            continue
        out.append(f"\n## {kind.value} — {report.total_by_kind(kind):,.2f} EUR\n")
        out.append("| Actif | Quantité | Valeur | Variation 7j | P&L réalisé | Frais | Tx |")
        out.append("|---|---|---|---|---|---|---|")
        for l in kind_lines:
            pct_str = f"{l.value_delta_pct:+.1f}%" if l.value_delta_pct is not None else "nouveau"
            out.append(
                f"| {l.symbol} | {l.quantity_now:.4f} | {l.value_eur_now:,.2f} EUR | "
                f"{l.value_delta_eur:+,.2f} EUR ({pct_str}) | {l.realized_pnl_eur:+,.2f} EUR | "
                f"{l.fees_eur:,.2f} EUR | {l.tx_count} |"
            )

    return "\n".join(out)


def narrate(report: WeeklyReport, llm_call: Callable[[str], str]) -> str:
    """Point d'extension optionnel : passe une fonction `llm_call(prompt) -> str`
    (ex: un wrapper autour de l'API Anthropic/OpenAI) pour obtenir un
    résumé en 3-4 phrases à partir du rapport déjà calculé.

    Le prompt embarque le Markdown généré par `render_markdown` et demande
    explicitement au modèle de ne pas introduire de chiffre absent de ce
    texte -- le LLM reformule, il ne recalcule jamais.

    Pas branché par défaut : `build_weekly_report` + `render_markdown`
    suffisent pour un rapport complet et fiable sans dépendance externe.
    """
    prompt = (
        "Voici un rapport de portefeuille structuré, avec des chiffres déjà "
        "calculés. Rédige un résumé factuel de 3 à 4 phrases en français, "
        "en reprenant uniquement les chiffres fournis ci-dessous -- n'en "
        "invente aucun :\n\n" + render_markdown(report)
    )
    return llm_call(prompt)
