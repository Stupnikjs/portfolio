"""Types pour le pipeline de données fondamentales (actions uniquement).

Suit le même style que src/schema.py du projet principal : dataclasses
simples, tout optionnel par défaut pour rester tolérant à des données
Yahoo manquantes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Valuation:
    pe_trailing: Optional[float] = None
    pe_forward: Optional[float] = None
    peg_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    price_to_sales: Optional[float] = None
    price_to_book: Optional[float] = None


@dataclass
class Profitability:
    fcf_eur_m: Optional[float] = None
    fcf_yield_pct: Optional[float] = None
    gross_margin_pct: Optional[float] = None
    operating_margin_pct: Optional[float] = None
    roe_pct: Optional[float] = None


@dataclass
class Growth:
    revenue_growth_yoy_pct: Optional[float] = None
    eps_growth_yoy_pct: Optional[float] = None


@dataclass
class BalanceSheet:
    net_debt_eur_m: Optional[float] = None
    debt_to_equity: Optional[float] = None


@dataclass
class Analyst:
    target_price_eur: Optional[float] = None
    rating_consensus: Optional[str] = None
    n_analysts: Optional[int] = None


@dataclass
class HardData:
    """Données factuelles, exclusivement récupérées via Yahoo (voir
    hard_data.py) -- jamais devinées ou remplies par un LLM."""

    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap_eur: Optional[float] = None
    valuation: Valuation = field(default_factory=Valuation)
    profitability: Profitability = field(default_factory=Profitability)
    growth: Growth = field(default_factory=Growth)
    balance_sheet: BalanceSheet = field(default_factory=BalanceSheet)
    analyst: Analyst = field(default_factory=Analyst)
    source: str = "yahoo_quotesummary"
    fetched_at: Optional[str] = None


@dataclass
class InvalidationCriterion:
    condition: str
    status: str = "not_triggered"  # not_triggered | triggered


@dataclass
class Thesis:
    """État de la thèse d'investissement. `initial_thesis`,
    `initial_date` et `invalidation_criteria[].condition` ne sont
    jamais réécrits par le LLM (voir ingest.py) -- seuls `status`,
    `last_reviewed`, `review_notes` et le `status` de chaque critère
    le sont."""

    initial_thesis: Optional[str] = None
    initial_date: Optional[str] = None
    invalidation_criteria: List[InvalidationCriterion] = field(default_factory=list)
    status: str = "valid"  # valid | watch | invalidated
    last_reviewed: Optional[str] = None
    review_notes: Optional[str] = None


@dataclass
class Narrative:
    recent_catalysts: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    changed_since_last: Optional[str] = None


@dataclass
class Meta:
    last_llm_update: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    confidence: Optional[str] = None  # low | medium | high


@dataclass
class FundamentalSnapshot:
    symbol: str
    ticker: str
    as_of: str
    hard_data: HardData = field(default_factory=HardData)
    thesis: Thesis = field(default_factory=Thesis)
    narrative: Narrative = field(default_factory=Narrative)
    meta: Meta = field(default_factory=Meta)
