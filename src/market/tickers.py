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

@lru_cache(maxsize=2048)
def ticker_for_stock(symbol: str) -> Optional[str]:
    symbol = symbol.upper()
    
    # 1. Traduire le symbole XTB en symbole Yahoo probable
    yahoo_symbol_guess = symbol
    for xtb_suf, yahoo_suf in _XTB_TO_YAHOO_SUFFIX.items():
        if symbol.endswith(xtb_suf):
            yahoo_symbol_guess = symbol[:-len(xtb_suf)] + yahoo_suf
            break

    # 2. Tentative 1 : Rechercher avec le symbole traduit
    try:
        resp = requests.get(
            _YAHOO_SEARCH_API,
            params={"q": yahoo_symbol_guess, "quotesCount": 1, "newsCount": 0},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        resp.raise_for_status()
        quotes = resp.json().get("quotes", [])
        if quotes:
            return quotes[0].get("symbol")
    except (requests.RequestException, ValueError, KeyError):
        pass

    # 3. Tentative 2 : Fallback avec le symbole original (au cas où)
    if yahoo_symbol_guess != symbol:
        try:
            resp = requests.get(
                _YAHOO_SEARCH_API,
                params={"q": symbol, "quotesCount": 1, "newsCount": 0},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            resp.raise_for_status()
            quotes = resp.json().get("quotes", [])
            if quotes:
                return quotes[0].get("symbol")
        except (requests.RequestException, ValueError, KeyError):
            pass
            
    return None

def resolve_ticker(symbol: str, kind: AssetKind) -> Optional[str]:
    if kind == AssetKind.CRYPTO:
        return ticker_for_crypto(symbol)
    if kind == AssetKind.STOCK:
        return ticker_for_stock(symbol)
    return None