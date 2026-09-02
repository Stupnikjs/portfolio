# src/report/llm_prompt.py
import json
import math
import requests
from datetime import datetime, timedelta, timezone

from ..store.serialize import TxStore
from ..ledger.portfolio import portfolio_snapshot_at
from ..ledger.cost_basis import compute_fifo
from ..market.prices import historical_price_eur
from ..schema import AssetKind

_YAHOO_QUOTE_SUMMARY = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=summaryProfile,financialData,summaryDetail"

def _get_yahoo_fundamentals(ticker: str) -> dict:
    if not ticker:
        return {}
    try:
        url = _YAHOO_QUOTE_SUMMARY.format(ticker=ticker)
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("quoteSummary", {}).get("result", [{}])[0]
        
        profile = data.get("summaryProfile", {})
        fin_data = data.get("financialData", {})
        detail = data.get("summaryDetail", {})
        
        return {
            "sector": profile.get("sector", "N/A"),
            "pe_ratio": fin_data.get("trailingPE", {}).get("raw"),
            "dividend_yield_pct": round(detail.get("dividendYield", {}).get("raw", 0) * 100, 2) if detail.get("dividendYield") else 0,
            "beta": detail.get("beta", {}).get("raw")
        }
    except Exception:
        return {}

def _calculate_returns(symbol: str, kind_str: str, ticker: str, days: int = 90) -> list:
    """Récupère l'historique de prix et calcule les rendements journaliers."""
    kind = AssetKind(kind_str) # Conversion string -> Enum
    end_date = datetime.now(timezone.utc)
    prices = []
    
    for i in range(days):
        dt = end_date - timedelta(days=i)
        try:
            price = historical_price_eur(symbol, dt, kind, ticker)
            if price > 0:
                prices.append(price)
        except Exception:
            continue
            
    returns = []
    for i in range(1, len(prices)):
        if prices[i-1] > 0:
            returns.append((prices[i] - prices[i-1]) / prices[i-1])
    return returns

def _pearson_correlation(x: list, y: list) -> float:
    n = min(len(x), len(y))
    if n < 5: return 0.0
        
    x = x[-n:]
    y = y[-n:]
    
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = math.sqrt(sum((xi - mean_x)**2 for xi in x))
    den_y = math.sqrt(sum((yi - mean_y)**2 for yi in y))
    
    if den_x == 0 or den_y == 0: return 0.0
    return num / (den_x * den_y)

def _build_correlation_matrix(assets_data: list) -> dict:
    returns_map = {}
    for asset in assets_data:
        # On limite à 30 jours pour l'API pour éviter de timeout si beaucoup d'actifs
        returns = _calculate_returns(asset['symbol'], asset['kind'], asset['ticker'], 30)
        if len(returns) > 5:
            returns_map[asset['symbol']] = returns
            
    matrix = {}
    symbols = list(returns_map.keys())
    
    for i in range(len(symbols)):
        sym1 = symbols[i]
        matrix[sym1] = {}
        for j in range(len(symbols)):
            sym2 = symbols[j]
            if i == j:
                continue
            elif i < j:
                corr = _pearson_correlation(returns_map[sym1], returns_map[sym2])
                matrix[sym1][sym2] = round(corr, 2)
                
    return matrix

def generate_fundamental_llm_prompt(tx_store: TxStore) -> str:
    snapshot = portfolio_snapshot_at(tx_store)
    cost_basis = compute_fifo(tx_store)
    
    total_value = snapshot['total_value_eur']
    open_positions = []
    assets_for_corr = []
    
    for asset in snapshot['assets']:
        symbol = asset['symbol']
        if asset['value_eur'] < 1.0 or asset['kind'] == 'Cash':
            continue
            
        avg_cost = cost_basis.average_cost(symbol)
        cost_basis_total = cost_basis.open_cost_basis(symbol)
        current_price = asset['price_eur']
        
        unrealized_pnl_eur = (current_price - avg_cost) * asset['quantity'] if avg_cost else 0
        unrealized_pnl_pct = ((current_price - avg_cost) / avg_cost) * 100 if avg_cost and avg_cost > 0 else 0
        
        open_lots = cost_basis.open_lots.get(symbol, [])
        oldest_lot_date = open_lots[0].acquired_at.strftime("%Y-%m-%d") if open_lots else "N/A"
        holding_days = (datetime.now(timezone.utc) - open_lots[0].acquired_at).days if open_lots else 0

        position = {
            "symbol": symbol,
            "asset_type": asset['kind'],
            "weight_in_portfolio_pct": round(asset['value_eur'] / total_value * 100, 2) if total_value > 0 else 0,
            "financials": {
                "cost_basis_eur": round(cost_basis_total, 2),
                "current_value_eur": round(asset['value_eur'], 2),
                "unrealized_pnl_eur": round(unrealized_pnl_eur, 2),
                "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
                "holding_period_days": holding_days,
                "oldest_lot_date": oldest_lot_date
            }
        }
        
        if asset['kind'] == 'Stock' and asset.get('ticker'):
            position["fundamentals"] = _get_yahoo_fundamentals(asset['ticker'])
        elif asset['kind'] == 'Crypto':
            position["fundamentals"] = {"category": "Layer 1 / DeFi / Meme"} 
            
        assets_for_corr.append({
            "symbol": symbol,
            "kind": asset['kind'],
            "ticker": asset.get('ticker')
        })
        open_positions.append(position)

    print("Calcul de la matrice de corrélation (Cela peut prendre quelques secondes)...")
    correlation_matrix = _build_correlation_matrix(assets_for_corr)

    prompt_payload = {
        "system_prompt": (
            "Tu es un analyste financier senior expert en analyse fondamentale et en gestion des risques. "
            "Tu ignores l'analyse technique. Ton but est d'évaluer la qualité de mes investissements, "
            "la justification de mon P/L, et la vraie diversification de mon portefeuille via la matrice de corrélation."
        ),
        "user_prompt": {
            "instructions": [
                "1. Analyse du P/L Fondamental : Pour chaque position, explique si le P/L est justifié par les fondamentaux.",
                "2. Analyse de la Vraie Diversification : Analyse la 'correlation_matrix'. Identifie les faux-amis (assets > 0.8) et les couvre-risques (< 0.2).",
                "3. Horizon de placement : Croise le P/L avec le 'holding_period_days'.",
                "4. Recommandation : Propose une réallocation pour optimiser le couple rendement/risque en jouant sur les corrélations."
            ],
            "portfolio_data": {
                "meta": {
                    "date_evaluation": snapshot['date'],
                    "total_value_eur": round(total_value, 2)
                },
                "correlation_matrix_30d": correlation_matrix,
                "open_positions": open_positions
            }
        }
    }
    
    return json.dumps(prompt_payload, indent=2, ensure_ascii=False)