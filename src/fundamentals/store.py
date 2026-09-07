"""Persistance des snapshots fondamentaux :

- data/fundamentals/<SYMBOL>.json        -- état courant (hard_data uniquement)
- data/fundamentals/history/<SYMBOL>.jsonl -- hard_data des anciens
  snapshots, une ligne par refresh, append-only (jamais réécrit en
  entier), pour pouvoir tracer/plotter l'évolution des métriques dans
  le temps.

La thèse d'investissement (invariable) et les évaluations hebdomadaires
du LLM vivent dans un store séparé -- voir thesis_store.py -- justement
pour qu'aucun refresh ici ne puisse jamais y toucher.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from .schema import (
    Analyst,
    BalanceSheet,
    FundamentalSnapshot,
    Growth,
    HardData,
    Profitability,
    Valuation,
)

FUND_DIR = Path("data/fundamentals")
HISTORY_DIR = FUND_DIR / "history"


def _current_path(symbol: str) -> Path:
    return FUND_DIR / f"{symbol}.json"


def _history_path(symbol: str) -> Path:
    return HISTORY_DIR / f"{symbol}.jsonl"


def _hard_data_from_dict(d: dict) -> HardData:
    return HardData(
        sector=d.get("sector"),
        industry=d.get("industry"),
        market_cap_eur=d.get("market_cap_eur"),
        valuation=Valuation(**d.get("valuation", {})),
        profitability=Profitability(**d.get("profitability", {})),
        growth=Growth(**d.get("growth", {})),
        balance_sheet=BalanceSheet(**d.get("balance_sheet", {})),
        analyst=Analyst(**d.get("analyst", {})),
        source=d.get("source", "yahoo_quotesummary"),
        fetched_at=d.get("fetched_at"),
    )


def snapshot_from_dict(d: dict) -> FundamentalSnapshot:
    return FundamentalSnapshot(
        symbol=d["symbol"],
        ticker=d["ticker"],
        as_of=d["as_of"],
        hard_data=_hard_data_from_dict(d.get("hard_data", {})),
    )


def load_fundamentals(symbol: str) -> Optional[FundamentalSnapshot]:
    path = _current_path(symbol)
    if not path.exists():
        return None
    return snapshot_from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_fundamentals(symbol: str, snapshot: FundamentalSnapshot) -> None:
    """Écrase le fichier courant, mais archive d'abord l'ANCIEN hard_data
    (celui qui existait avant cet appel) dans l'historique append-only --
    jamais celui qu'on est en train d'écrire, pour ne jamais dupliquer un
    même snapshot deux fois dans l'historique."""
    old = load_fundamentals(symbol)
    if old is not None:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        entry = {"as_of": old.as_of, "hard_data": asdict(old.hard_data)}
        with _history_path(symbol).open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    FUND_DIR.mkdir(parents=True, exist_ok=True)
    _current_path(symbol).write_text(
        json.dumps(asdict(snapshot), indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_history(symbol: str) -> List[dict]:
    """Renvoie la liste des anciens snapshots hard_data, dans l'ordre
    chronologique -- prête à être passée à chart_display_v0 ou matplotlib
    pour tracer l'évolution d'une métrique (ex: pe_forward) dans le temps."""
    path = _history_path(symbol)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]