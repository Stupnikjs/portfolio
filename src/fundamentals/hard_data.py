"""Récupération des données fondamentales factuelles ("hard data") d'une
action via l'API quoteSummary de Yahoo Finance -- aucun LLM, aucun coût,
aucune hallucination possible sur les chiffres.

Best-effort, comme market/prices.py et market/tickers.py du projet
principal : un échec réseau ne doit jamais casser le refresh des autres
actifs du portefeuille, donc on renvoie None plutôt que de lever.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import requests

from .schema import Analyst, BalanceSheet, Growth, HardData, Profitability, Valuation

_YAHOO_MODULES = "quoteType,assetProfile,financialData,defaultKeyStatistics,summaryDetail"
_YAHOO_QUOTE_SUMMARY = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
_YAHOO_CRUMB_URL = "https://query2.finance.yahoo.com/v1/test/getcrumb"

# Types Yahoo traités comme des actions -- tout le reste (ETF, MUTUALFUND,
# CRYPTOCURRENCY, INDEX...) est explicitement exclu du pipeline fundamentals
# actions : Yahoo ne fournit pas de financialData exploitable pour un ETF
# (PE, marges, etc. n'ont pas de sens pour un panier de titres).
_EQUITY_QUOTE_TYPES = {"EQUITY"}

# Session module-level réutilisée entre tickers : quoteSummary exige
# désormais un cookie de session + un "crumb" (contrairement à
# chart/search, utilisés dans market/prices.py et market/tickers.py, qui
# n'en ont pas besoin). On récupère le crumb une seule fois et on le
# réutilise pour tous les appels du run.
_session: Optional[requests.Session] = None
_crumb: Optional[str] = None


def _get_session_and_crumb() -> tuple[requests.Session, Optional[str]]:
    global _session, _crumb
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": "Mozilla/5.0"})
        try:
            # Un premier hit sur le domaine pose les cookies nécessaires
            # avant de demander le crumb.
            _session.get("https://fc.yahoo.com", timeout=10)
            resp = _session.get(_YAHOO_CRUMB_URL, timeout=10)
            resp.raise_for_status()
            _crumb = resp.text.strip()
        except requests.RequestException as e:
            print(f"  [WARN] Impossible d'obtenir le crumb Yahoo : {e}")
            _crumb = None
    return _session, _crumb


def _get(d: dict, key: str, default=None):
    """Lit une valeur dans un dict Yahoo, en dépliant le format
    {"raw": ..., "fmt": ...} utilisé pour la plupart des champs numériques.
    Un champ manquant ou vide côté Yahoo peut arriver sous forme de dict
    sans clé "raw" (ex: {}) -- il faut le traiter comme absent (None),
    jamais le retourner tel quel."""
    val = d.get(key, default)
    if isinstance(val, dict):
        return val.get("raw", default)
    return val if val is not None else default


def _pct(ratio: Optional[float]) -> Optional[float]:
    return round(ratio * 100, 2) if ratio is not None else None


def fetch_hard_data(ticker: str) -> Optional[HardData]:
    session, crumb = _get_session_and_crumb()
    url = _YAHOO_QUOTE_SUMMARY.format(ticker=ticker)
    params = {"modules": _YAHOO_MODULES}
    if crumb:
        params["crumb"] = crumb

    try:
        resp = session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        result = resp.json().get("quoteSummary", {}).get("result")
        if not result:
            print(f"  [WARN] Yahoo : pas de résultat pour {ticker} (status {resp.status_code})")
            return None
        data = result[0]
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"  [WARN] Yahoo quoteSummary KO pour {ticker} : {e}")
        return None

    quote_type = _get(data.get("quoteType", {}), "quoteType")
    if quote_type not in _EQUITY_QUOTE_TYPES:
        print(f"  [SKIP] {ticker} n'est pas une action (quoteType={quote_type!r}), exclu du pipeline fundamentals")
        return None

    profile = data.get("assetProfile", {})
    fin = data.get("financialData", {})
    stats = data.get("defaultKeyStatistics", {})
    detail = data.get("summaryDetail", {})

    market_cap_eur = _get(detail, "marketCap")
    fcf_raw = _get(fin, "freeCashflow")
    fcf_eur_m = round(fcf_raw / 1_000_000, 2) if fcf_raw is not None else None
    fcf_yield_pct = (
        round(fcf_raw / market_cap_eur * 100, 2)
        if fcf_raw is not None and market_cap_eur
        else None
    )

    return HardData(
        sector=profile.get("sector"),
        industry=profile.get("industry"),
        market_cap_eur=market_cap_eur,
        valuation=Valuation(
            pe_trailing=_get(detail, "trailingPE"),
            pe_forward=_get(stats, "forwardPE"),
            peg_ratio=_get(stats, "pegRatio"),
            ev_ebitda=_get(stats, "enterpriseToEbitda"),
            price_to_sales=_get(stats, "priceToSalesTrailing12Months"),
            price_to_book=_get(stats, "priceToBook"),
        ),
        profitability=Profitability(
            fcf_eur_m=fcf_eur_m,
            fcf_yield_pct=fcf_yield_pct,
            gross_margin_pct=_pct(_get(fin, "grossMargins")),
            operating_margin_pct=_pct(_get(fin, "operatingMargins")),
            roe_pct=_pct(_get(fin, "returnOnEquity")),
        ),
        growth=Growth(
            revenue_growth_yoy_pct=_pct(_get(fin, "revenueGrowth")),
            eps_growth_yoy_pct=_pct(_get(fin, "earningsGrowth")),
        ),
        balance_sheet=BalanceSheet(
            net_debt_eur_m=None,  # non fourni par ce module Yahoo
            debt_to_equity=_get(fin, "debtToEquity"),
        ),
        analyst=Analyst(
            target_price_eur=_get(fin, "targetMeanPrice"),
            rating_consensus=_get(fin, "recommendationKey"),
            n_analysts=_get(fin, "numberOfAnalystOpinions"),
        ),
        source="yahoo_quotesummary",
        fetched_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )