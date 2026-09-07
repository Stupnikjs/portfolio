"""Point d'entrée du pipeline fondamentaux (actions uniquement).

Usage :
  python -m src.fundamentals.cli refresh MSTR
  python -m src.fundamentals.cli refresh --all
  python -m src.fundamentals.cli thesis-init MSTR "thèse initiale" \\
      --criteria fcf_yield:"FCF yield < 3%" guidance:"guidance revue à la baisse"
  python -m src.fundamentals.cli review-prompt --all
  python -m src.fundamentals.cli review-ingest reponse.json

`refresh` n'appelle aucun LLM (juste Yahoo, gratuit) -- peut tourner
aussi souvent que voulu. `review-prompt`/`review-ingest` sont le flux
manuel de revue hebdomadaire : tu copies le texte affiché par
`review-prompt` dans un chat, tu sauvegardes sa réponse JSON dans un
fichier, puis `review-ingest`.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from ..schema import AssetKind
from ..store.serialize import load_wallet
from .hard_data import fetch_hard_data
from .ingest import ingest_weekly_review
from .prompt_builder import build_weekly_review_prompt
from .schema import FundamentalSnapshot, InvalidationCriterion, ThesisDefinition
from .store import load_fundamentals, load_thesis, save_fundamentals, save_thesis

TX_STORE_PATH = Path("./data/tx_store.json")


def _stock_symbols(tx_store) -> dict[str, str]:
    """Renvoie {symbol: ticker} pour les actions du wallet uniquement."""
    return {
        symbol: asset.identifiers.ticker
        for symbol, asset in tx_store.assets.items()
        if asset.kind == AssetKind.STOCK and asset.identifiers.ticker
    }


def _refresh_one(symbol: str, ticker: str) -> None:
    hd = fetch_hard_data(ticker)
    if hd is None:
        print(f"  [WARN] Yahoo n'a rien renvoyé pour {ticker}, refresh ignoré")
        return

    current = load_fundamentals(symbol)
    snapshot = current or FundamentalSnapshot(symbol=symbol, ticker=ticker, as_of="")
    snapshot.hard_data = hd
    snapshot.as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    save_fundamentals(symbol, snapshot)
    print(f"  \u2713 {symbol:<10} hard_data actualis\u00e9")


def cmd_refresh(args: argparse.Namespace) -> None:
    tx_store = load_wallet(TX_STORE_PATH)
    if args.all:
        for symbol, ticker in _stock_symbols(tx_store).items():
            _refresh_one(symbol, ticker)
    else:
        asset = tx_store.assets.get(args.symbol)
        ticker = asset.identifiers.ticker if asset and asset.identifiers.ticker else args.symbol
        _refresh_one(args.symbol, ticker)


def cmd_thesis_init(args: argparse.Namespace) -> None:
    if load_thesis(args.symbol) is not None and not args.force:
        print(f"  [ERREUR] une thèse existe déjà pour {args.symbol} (--force pour écraser)")
        return

    tx_store = load_wallet(TX_STORE_PATH)
    asset = tx_store.assets.get(args.symbol)
    ticker = asset.identifiers.ticker if asset and asset.identifiers.ticker else args.symbol

    criteria = []
    for raw in args.criteria or []:
        crit_id, _, condition = raw.partition(":")
        if not condition:
            print(f"  [ERREUR] critère mal formé (attendu id:condition) : {raw!r}")
            return
        criteria.append(InvalidationCriterion(id=crit_id, condition=condition))

    thesis = ThesisDefinition(
        symbol=args.symbol,
        ticker=ticker,
        text=args.thesis,
        invalidation_criteria=criteria,
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )
    save_thesis(args.symbol, thesis)
    print(f"  \u2713 Th\u00e8se enregistr\u00e9e pour {args.symbol} ({len(criteria)} crit\u00e8re(s))")


def cmd_review_prompt(args: argparse.Namespace) -> None:
    tx_store = load_wallet(TX_STORE_PATH)
    stock_symbols = _stock_symbols(tx_store)

    symbols = list(stock_symbols) if args.all else args.symbols
    theses, fundamentals = [], {}
    for symbol in symbols:
        thesis = load_thesis(symbol)
        snapshot = load_fundamentals(symbol)
        if thesis is None:
            print(f"  [SKIP] pas de thèse pour {symbol} (lance 'thesis-init' d'abord)")
            continue
        if snapshot is None:
            print(f"  [SKIP] pas de hard_data pour {symbol} (lance 'refresh {symbol}' d'abord)")
            continue
        theses.append(thesis)
        fundamentals[symbol] = snapshot

    if not theses:
        print("  [ERREUR] aucun actif prêt pour la revue")
        return

    print(build_weekly_review_prompt(theses, fundamentals))


def cmd_review_ingest(args: argparse.Namespace) -> None:
    ingested = ingest_weekly_review(Path(args.response_file))
    print(f"  \u2713 {len(ingested)} actif(s) mis \u00e0 jour : {', '.join(ingested)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline fondamentaux (actions)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_refresh = sub.add_parser("refresh", help="Actualise hard_data depuis Yahoo (pas de LLM)")
    p_refresh.add_argument("symbol", nargs="?", help="Symbole (ignor\u00e9 si --all)")
    p_refresh.add_argument("--all", action="store_true", help="Toutes les actions du wallet")
    p_refresh.set_defaults(func=cmd_refresh)

    p_thesis = sub.add_parser("thesis-init", help="Enregistre la thèse et ses critères d'invalidation")
    p_thesis.add_argument("symbol")
    p_thesis.add_argument("thesis")
    p_thesis.add_argument("--criteria", nargs="*", help="Un par argument, format id:condition")
    p_thesis.add_argument("--force", action="store_true", help="Écrase une thèse existante")
    p_thesis.set_defaults(func=cmd_thesis_init)

    p_review_prompt = sub.add_parser("review-prompt", help="Génère le prompt de revue hebdo (batch)")
    p_review_prompt.add_argument("symbols", nargs="*", help="Symboles à revoir (ignoré si --all)")
    p_review_prompt.add_argument("--all", action="store_true", help="Toutes les actions ayant une thèse")
    p_review_prompt.set_defaults(func=cmd_review_prompt)

    p_review_ingest = sub.add_parser("review-ingest", help="Ingère la réponse LLM batch collée dans un fichier")
    p_review_ingest.add_argument("response_file")
    p_review_ingest.set_defaults(func=cmd_review_ingest)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()