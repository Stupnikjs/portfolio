# src/ledger/metrics.py
from datetime import datetime, timedelta, timezone
from typing import Optional
import math
from ..store.serialize import TxStore
from ..ledger.positions import holdings_at
from ..market.prices import historical_price_eur
from ..schema import AssetKind, TransactionKind

RF_ANNUAL = 0.03  # taux sans risque ECB, ajustable

def _portfolio_value_series(tx_store: TxStore, start: datetime, end: datetime) -> list[tuple[datetime, float]]:
    """Reconstruit la valeur totale du portefeuille EUR pour chaque jour
    entre start et end. Coûteux en appels API — à cacher côté caller."""
    series = []
    cur = start
    while cur <= end:
        holdings = holdings_at(tx_store, cur)
        v = 0.0
        for sym, qty in holdings.items():
            if abs(qty) < 1e-12:
                continue
            asset = tx_store.assets.get(sym)
            kind = asset.kind if asset else AssetKind.CRYPTO
            ticker = asset.identifiers.ticker if asset else None
            try:
                v += qty * historical_price_eur(sym, cur, kind, ticker)
            except Exception:
                pass
        series.append((cur, v))
        cur += timedelta(days=1)
    return series

def _external_cash_flows(tx_store: TxStore) -> list[tuple[datetime, float]]:
    """Deposits = +, Withdraws = - (en EUR). Utilisé pour IRR et pour
    découper le TWR en sous-périodes."""
    flows = []
    for tx in tx_store.transactions:
        if tx.kind == TransactionKind.DEPOSITE and tx.asset.symbol in ("EUR", "EURI"):
            flows.append((tx.time, tx.value_eur))
        elif tx.kind == TransactionKind.WITHDRAW and tx.asset.symbol in ("EUR", "EURI"):
            flows.append((tx.time, -tx.value_eur))
    return sorted(flows, key=lambda x: x[0])

def _twr(series: list[tuple[datetime, float]], flows: list[tuple[datetime, float]]) -> float:
    """Time-Weighted Return : neutralise l'effet des apports/retraits."""
    if not series:
        return 0.0
    # Sous-périodes = segments séparés par chaque flux
    sub_returns = []
    last_value = series[0][1]
    flow_idx = 0
    for i in range(1, len(series)):
        # Flux entre la veille et aujourd'hui ? on clôt la sous-période
        while flow_idx < len(flows) and flows[flow_idx][0] <= series[i][0]:
            # corrige la valeur de fin en retirant le flux entré ce jour
            sub = (last_value + flows[flow_idx][1]) / last_value - 1 if last_value else 0
            sub_returns.append(sub)
            last_value += flows[flow_idx][1]
            flow_idx += 1
        sub = series[i][1] / last_value - 1 if last_value else 0
        sub_returns.append(sub)
        last_value = series[i][1]
    return math.prod(1 + r for r in sub_returns) - 1

def _xirr(flows: list[tuple[datetime, float]], guess: float = 0.1, tol: float = 1e-6, max_iter: int = 100) -> float:
    """Money-Weighted Return (XIRR) — Newton-Raphson."""
    t0 = flows[0][0]
    def npv(r):
        return sum(cf / (1 + r) ** ((t - t0).days / 365.0) for t, cf in flows)
    def dnpv(r):
        return sum(-(t - t0).days / 365.0 * cf / (1 + r) ** ((t - t0).days / 365.0 + 1)
                   for t, cf in flows)
    r = guess
    for _ in range(max_iter):
        f, df = npv(r), dnpv(r)
        if abs(df) < 1e-12:
            break
        r_new = r - f / df
        if abs(r_new - r) < tol:
            return r_new
        r = r_new
    return r

def _daily_returns(series):
    out = []
    for i in range(1, len(series)):
        if series[i-1][1] > 0:
            out.append((series[i][1] - series[i-1][1]) / series[i-1][1])
    return out

def _max_drawdown(series):
    peak = -math.inf
    max_dd = 0.0
    for _, v in series:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd

def _var_cvar(returns: list[float], alpha: float = 0.05) -> tuple[float, float]:
    """VaR et CVaR historiques (pertes en valeur négative)."""
    if not returns:
        return 0.0, 0.0
    s = sorted(returns)
    n = max(1, int(len(s) * alpha))
    var = -s[n-1]
    cvar = -sum(s[:n]) / n
    return var, cvar

def compute_portfolio_metrics(tx_store: TxStore, lookback_days: int = 365) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    series = _portfolio_value_series(tx_store, start, end)
    flows = [(t, cf) for t, cf in _external_cash_flows(tx_store) if start <= t <= end]
    flows.append((end, -series[-1][1]))  # valorisation finale = flux sortant hypothétique

    twr = _twr(series, [f for f in _external_cash_flows(tx_store) if start <= f[0] <= end])
    irr = _xirr(flows) if len(flows) > 1 else 0.0
    rets = _daily_returns(series)
    vol_daily = math.sqrt(sum(r*r for r in rets) / max(1, len(rets)))
    vol_annual = vol_daily * math.sqrt(252)
    annual_return = twr * 252 / max(1, lookback_days)  # approximation
    sharpe = (annual_return - RF_ANNUAL) / vol_annual if vol_annual > 0 else 0.0
    max_dd = _max_drawdown(series)
    var95, cvar95 = _var_cvar(rets, 0.05)
    var99, cvar99 = _var_cvar(rets, 0.01)

    return {
        "lookback_days": lookback_days,
        "twr_pct": round(twr * 100, 2),
        "irr_pct": round(irr * 100, 2),
        "volatility_annual_pct": round(vol_annual * 100, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "var_95_1d_pct": round(var95 * 100, 2),
        "cvar_95_1d_pct": round(cvar95 * 100, 2),
        "var_99_1d_pct": round(var99 * 100, 2),
        "cvar_99_1d_pct": round(cvar99 * 100, 2),
    }