"""Équivalent Python de pf_price::historical_price_eur.
Utilise l'API publique de Binance pour la crypto, et Yahoo Finance pour les actions.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

import requests

from ..schema import AssetKind

_BINANCE_API = "https://data-api.binance.vision/api/v3/klines"
_YAHOO_CHART_API = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

class PriceError(RuntimeError):
    pass


@lru_cache(maxsize=4096)
def _binance_klines(symbol_pair: str, day_str: str) -> list:
    time.sleep(0.1)
    dt = datetime.strptime(day_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start_ms = int(dt.timestamp() * 1000)

    resp = requests.get(
        _BINANCE_API,
        params={"symbol": symbol_pair, "interval": "1d", "startTime": start_ms, "limit": 1},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@lru_cache(maxsize=4096)
def _yahoo_historical_price(ticker: str, day_str: str) -> tuple[float, str]:
    """Récupère le prix de clôture et la devise via Yahoo Finance."""
    dt = datetime.strptime(day_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start_s = int(dt.timestamp())
    end_s = int((dt + timedelta(days=1)).timestamp())

    url = _YAHOO_CHART_API.format(ticker=ticker)
    resp = requests.get(
        url,
        params={"period1": start_s, "period2": end_s, "interval": "1d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    result = data.get("chart", {}).get("result", [])
    if not result:
        raise PriceError(f"Yahoo n'a pas trouvé de résultat pour {ticker}")

    meta = result[0].get("meta", {})
    currency = meta.get("currency", "USD").upper()

    closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
    if not closes or closes[0] is None:
        raise PriceError(f"Pas de prix de clôture pour {ticker} au {day_str}")

    return float(closes[0]), currency


def _get_price_from_binance(symbol: str, time: datetime) -> float:
    day_str = time.strftime("%Y-%m-%d")
    try:
        data = _binance_klines(f"{symbol}EUR", day_str)
        if data and len(data) > 0:
            return float(data[0][4])
    except requests.exceptions.HTTPError as e:
        if e.response.status_code != 400:
            raise PriceError(f"API Binance KO pour {symbol}EUR") from e

    try:
        usdt_data = _binance_klines(f"{symbol}USDT", day_str)
        eurusdt_data = _binance_klines("EURUSDT", day_str)
        if usdt_data and eurusdt_data and len(usdt_data) > 0 and len(eurusdt_data) > 0:
            price_usdt = float(usdt_data[0][4])
            eurusdt_rate = float(eurusdt_data[0][4])
            if eurusdt_rate > 0:
                return price_usdt / eurusdt_rate
    except Exception as e:
        raise PriceError(f"Pas de prix USDT/EUR pour {symbol}") from e

    raise PriceError(f"Binance n'a pas trouvé le prix pour {symbol} au {day_str}")


def historical_price_eur(symbol: str, time: datetime, kind: AssetKind, ticker: Optional[str] = None) -> float:
    """Retourne le prix en EUR de `symbol` à la date `time` en fonction de son `kind`."""
    symbol = symbol.upper()

    # Gestion des devises (Cash)
    if kind == AssetKind.CASH:
        if symbol in ("EUR", "EURI"):
            return 1.0
        if symbol in ("USD", "USDT", "USDC", "BUSD"):
            return 0.92  # Fixe, à remplacer par un vrai appel API si besoin
        if symbol in ("GBP",):
            return 1.15

    if time.tzinfo is None:
        time = time.replace(tzinfo=timezone.utc)

    day_str = time.strftime("%Y-%m-%d")

    # --- BRANCHE STOCK : YAHOO FINANCE ---
    if kind == AssetKind.STOCK:
        if not ticker:
            print(f"  [WARN] Pas de ticker Yahoo pour l'action {symbol}. Prix mis à 0.")
            return 0.0
        try:
            price, currency = _yahoo_historical_price(ticker, day_str)
            if currency != "EUR":
                fx_pair = f"EUR{currency}=X"
                fx_price, _ = _yahoo_historical_price(fx_pair, day_str)
                return price / fx_price
            return price
        except (PriceError, requests.RequestException):
            print(f"  [WARN] Prix Yahoo indisponible pour {ticker} au {day_str}.")
            return 0.0

    # --- BRANCHE CRYPTO : BINANCE ---
    if kind == AssetKind.CRYPTO:
        try:
            return _get_price_from_binance(symbol, time)
        except PriceError:
            print(f"  [WARN] Prix Binance indisponible pour {symbol} au {day_str}. Prix mis à 0.")
            return 0.0

    print(f"  [WARN] Type d'actif non géré pour {symbol}: {kind}")
    return 0.0