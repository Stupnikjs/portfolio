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
    """Récupère la dernière clôture Yahoo disponible <= day_str.

    Important : day_str peut tomber un week-end ou un jour férié.
    On demande une fenêtre de plusieurs jours et on prend la dernière
    bougie disponible avant ou à la date cible.
    """
    target = datetime.strptime(day_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    # 7 jours en arrière couvrent normalement week-ends + jours fériés.
    period1 = int((target - timedelta(days=7)).timestamp())
    period2 = int((target + timedelta(days=1)).timestamp())

    url = _YAHOO_CHART_API.format(ticker=ticker)

    resp = requests.get(
        url,
        params={
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "history",
        },
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    resp.raise_for_status()

    data = resp.json()

    result = data.get("chart", {}).get("result", [])
    if not result:
        raise PriceError(f"Yahoo n'a pas trouvé de résultat pour {ticker}")

    result = result[0]
    meta = result.get("meta", {})

    # Ne surtout pas faire .upper() : GBp != GBP.
    currency = meta.get("currency", "USD")

    timestamps = result.get("timestamp", [])
    closes = (
        result.get("indicators", {})
        .get("quote", [{}])[0]
        .get("close", [])
    )

    candidates = []

    for ts, close in zip(timestamps, closes):
        if close is None:
            continue

        dt = datetime.fromtimestamp(ts, tz=timezone.utc)

        if dt <= target:
            candidates.append((dt, float(close)))

    if not candidates:
        raise PriceError(
            f"Pas de clôture Yahoo disponible pour {ticker} "
            f"au plus tard le {day_str}"
        )

    used_date, price = max(candidates, key=lambda x: x[0])

    return price, currency

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


def _normalize_currency_for_fx(currency: str) -> tuple[str, float]:
    """Renvoie (devise à utiliser pour interroger la paire FX Yahoo,
    facteur multiplicatif à appliquer au prix). Nécessaire car Yahoo
    exprime certains titres londoniens en pence ("GBp") plutôt qu'en
    livres ("GBP") -- il n'existe pas de paire "EURGBp=X", il faut
    interroger "EURGBP=X" et diviser le prix en pence par 100 pour
    obtenir des livres avant conversion."""
    if currency in ("GBp", "GBX"):
        return "GBP", 0.01
    return currency, 1.0


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
                fx_currency, price_factor = _normalize_currency_for_fx(currency)
                price = price * price_factor
                fx_pair = f"EUR{fx_currency}=X"
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