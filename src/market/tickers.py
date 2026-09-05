"""src/tickers.py

Résolution du ticker externe (AssetIdentifiers.ticker) pour un Asset :
- STOCK  -> recherche Yahoo Finance (endpoint non officiel), utile car le
  symbole XTB (ex: 'CDR.PL') ne correspond pas forcément à la notation
  Yahoo (ex: 'CDR.WA' pour la Bourse de Varsovie).
- CRYPTO -> API publique Binance (exchangeInfo, déjà utilisée dans
  prices.py) : confirme que le symbole est bien un actif de base coté sur
  Binance et renvoie ce même symbole comme ticker.

Best-effort : toute erreur réseau/format renvoie None plutôt que de
lever une exception -- un ticker manquant ne doit jamais bloquer le
pipeline de construction du wallet.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional, Set

import requests

from ..schema import AssetKind

_YAHOO_SEARCH_API = "https://query2.finance.yahoo.com/v1/finance/search"
_BINANCE_EXCHANGE_INFO = "https://data-api.binance.vision/api/v3/exchangeInfo"

# Mapping des suffixes XTB -> Yahoo Finance
_XTB_TO_YAHOO_SUFFIX = {
    ".FR": ".PA",  # Euronext Paris
    ".NL": ".AS",  # Euronext Amsterdam
    ".UK": ".L",   # London Stock Exchange
    ".DE": ".DE",  # Xetra (identique)
    ".US": "",     # Pas de suffixe pour les US (ex: MSTR.US -> MSTR)
    ".PL": ".WA",  # Varsovie
}

@lru_cache(maxsize=1)
def _binance_known_base_assets() -> Set[str]:
    try:
        resp = requests.get(_BINANCE_EXCHANGE_INFO, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {s["baseAsset"] for s in data.get("symbols", [])}
    except requests.RequestException:
        return set()

def ticker_for_crypto(symbol: str) -> Optional[str]:
    known = _binance_known_base_assets()
    symbol = symbol.upper()
    return symbol if symbol in known else None



# Corrections manuelles pour les cas où la recherche Yahoo se trompe
# systématiquement (nom trop générique, ou concurrence avec des produits
# dérivés/leveraged plus "populaires" que l'actif sous-jacent recherché).
_MANUAL_TICKER_OVERRIDES = {
    "MSTR.US": "MSTR",
    # Ajoute ici le symbole XTB exact affiché par le pipeline pour l'ETF
    # Vietnam une fois identifié, ex: "DBXVN.DE": "DBXVN.DE",
}

_ACCEPTED_QUOTE_TYPES = {"EQUITY", "ETF"}

_MANUAL_TICKER_OVERRIDES = {
    "MSTR.US": "MSTR",
    "XFVT.DE": "XFVT.DE",  # plusieurs classes de parts homonymes (.MI/.SW/.L) -> ambigu pour la recherche Yahoo
}

def _best_quote(quotes: list[dict], expected_symbol: str) -> Optional[str]:
    """Choisit le meilleur candidat parmi les résultats Yahoo :
    1. correspondance EXACTE du symbole complet (gère le cas d'un même
       fonds coté sur plusieurs places avec un radical identique, ex:
       XFVT.DE / XFVT.MI / XFVT.SW / XFVT.L) ;
    2. à défaut, même radical (avant le point) et type EQUITY/ETF, pour
       éviter les produits dérivés au nom proche (ex: MSTU/MSTX pour MSTR).
    """
    candidates = [q for q in quotes if q.get("quoteType") in _ACCEPTED_QUOTE_TYPES]
    if not candidates:
        return None

    exact_symbol = [q for q in candidates if q.get("symbol", "").upper() == expected_symbol.upper()]
    if exact_symbol:
        return exact_symbol[0].get("symbol")

    expected_root = expected_symbol.split(".")[0].upper()
    same_root = [q for q in candidates if q.get("symbol", "").split(".")[0].upper() == expected_root]
    if len(same_root) == 1:
        return same_root[0].get("symbol")

    return None  # ambigu (plusieurs places de cotation) -> mieux vaut échouer que se tromper


@lru_cache(maxsize=2048)
def ticker_for_stock(symbol: str) -> Optional[str]:
    symbol = symbol.upper()

    if symbol in _MANUAL_TICKER_OVERRIDES:
        return _MANUAL_TICKER_OVERRIDES[symbol]

    yahoo_symbol_guess = symbol
    for xtb_suf, yahoo_suf in _XTB_TO_YAHOO_SUFFIX.items():
        if symbol.endswith(xtb_suf):
            yahoo_symbol_guess = symbol[:-len(xtb_suf)] + yahoo_suf
            break

    for query in (yahoo_symbol_guess, symbol) if yahoo_symbol_guess != symbol else (yahoo_symbol_guess,):
        try:
            resp = requests.get(
                _YAHOO_SEARCH_API,
                params={"q": query, "quotesCount": 5, "newsCount": 0},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            resp.raise_for_status()
            quotes = resp.json().get("quotes", [])
            best = _best_quote(quotes, yahoo_symbol_guess)
            if best:
                return best
        except (requests.RequestException, ValueError, KeyError):
            pass

    return None


def resolve_ticker(symbol: str, kind: AssetKind) -> Optional[str]:
    if kind == AssetKind.CRYPTO:
        return ticker_for_crypto(symbol)
    if kind == AssetKind.STOCK:
        return ticker_for_stock(symbol)
    return None