"""Types pour la thèse d'investissement et son suivi dans le temps.

Séparé de fundamentals/schema.py à dessein : ThesisDefinition est écrite
une fois (thesis-init ou édition manuelle du JSON) et ne doit JAMAIS être
réécrite par le pipeline de revue hebdomadaire -- l'isoler dans son propre
fichier/store rend cette invariance structurelle plutôt qu'une simple
convention respectée par le code d'ingestion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class InvalidationCriterion:
    """Un scénario qui invaliderait la thèse. `id` et `condition` sont
    figés une fois écrits -- le LLM les recopie tel quel dans son
    évaluation, il ne les reformule jamais."""

    id: str            # court, stable, ex: "fcf_yield", "guidance_cut"
    condition: str      # texte libre, ex: "FCF yield tombe sous 3%"


@dataclass
class ThesisDefinition:
    """La thèse elle-même -- invariable. Modifiée uniquement par une
    action humaine explicite (thesis-init ou édition manuelle du JSON),
    jamais par un refresh ou une revue automatique."""

    symbol: str
    ticker: str
    text: str
    invalidation_criteria: List[InvalidationCriterion] = field(default_factory=list)
    created_at: str = ""


@dataclass
class CriterionEvaluation:
    id: str              # recopié tel quel depuis ThesisDefinition, jamais reformulé
    status: str            # not_triggered | watch | triggered
    note: str = ""


@dataclass
class ThesisEvaluation:
    """Une revue hebdomadaire -- immuable une fois écrite, append-only
    dans evaluations/<SYMBOL>.jsonl. Représente l'état de la conviction
    à un instant donné, pas une donnée qu'on corrige a posteriori."""

    evaluated_at: str
    criteria: List[CriterionEvaluation] = field(default_factory=list)
    overall_status: str = "valid"   # valid | watch | invalidated
    confidence: str = "medium"       # low | medium | high
    summary: str = ""
    sources: List[str] = field(default_factory=list)


 
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
class FundamentalSnapshot:
    """État courant des données factuelles d'un actif -- écrasé sans
    risque à chaque refresh, l'historique étant géré par store.py."""
 
    symbol: str
    ticker: str
    as_of: str
    hard_data: HardData = field(default_factory=HardData)
 