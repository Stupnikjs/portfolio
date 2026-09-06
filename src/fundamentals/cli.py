"""Point d'entrée du pipeline fondamentaux (actions uniquement).

Usage :
  python -m src.fundamentals.cli refresh MSTR
  python -m src.fundamentals.cli refresh --all
  python -m src.fundamentals.cli init MSTR "thèse initiale" --criteria "FCF yield < 3%" "..."
  python -m src.fundamentals.cli prompt MSTR
  python -m src.fundamentals.cli ingest MSTR reponse.json

`refresh` n'appelle aucun LLM (juste Yahoo, gratuit) -- peut tourner aussi
souvent que voulu, y compris à chaque build_wallet.py. `prompt`/`ingest`
sont le flux manuel : tu copies le texte affiché par `prompt` dans un
chat, tu sauvegardes sa réponse JSON dans un fichier, puis `ingest`.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from ..schema import AssetKind
from ..store.serialize import load_wallet
from .hard_data import fetch_hard_data
from .ingest import ingest_response
from .prompt_builder import build_update_prompt
from .schema import FundamentalSnapshot, InvalidationCriterion, Thesis
from .store import load_fundamentals, save_fundamentals

TX_STORE_PATH = Path("./data/tx_store.json")


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
        for symbol, asset in tx_store.assets.items():
            if asset.kind != AssetKind.STOCK or not asset.identifiers.ticker:
                continue
            _refresh_one(symbol, asset.identifiers.ticker)
    else:
        asset = tx_store.assets.get(args.symbol)
        ticker = asset.identifiers.ticker if asset and asset.identifiers.ticker else args.symbol
        _refresh_one(args.symbol, ticker)


def cmd_init(args: argparse.Namespace) -> None:
    current = load_fundamentals(args.symbol)
    if current is None:
        print(f"  [ERREUR] lance d'abord 'refresh {args.symbol}' pour cr\u00e9er le hard_data")
        return
    current.thesis = Thesis(
        initial_thesis=args.thesis,
        initial_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        invalidation_criteria=[InvalidationCriterion(condition=c) for c in (args.criteria or [])],
        status="valid",
    )
    save_fundamentals(args.symbol, current)
    print(f"  \u2713 Th\u00e8se initiale enregistr\u00e9e pour {args.symbol}")


def cmd_prompt(args: argparse.Namespace) -> None:
    current = load_fundamentals(args.symbol)
    if current is None:
        print(f"  [ERREUR] aucun fichier pour {args.symbol}, lance d'abord 'refresh'")
        return
    print(build_update_prompt(current))


def cmd_ingest(args: argparse.Namespace) -> None:
    ingest_response(args.symbol, Path(args.response_file))
    print(f"  \u2713 {args.symbol} mis \u00e0 jour \u00e0 partir de {args.response_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline fondamentaux (actions)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_refresh = sub.add_parser("refresh", help="Actualise hard_data depuis Yahoo (pas de LLM)")
    p_refresh.add_argument("symbol", nargs="?", help="Symbole (ignor\u00e9 si --all)")
    p_refresh.add_argument("--all", action="store_true", help="Toutes les actions du wallet")
    p_refresh.set_defaults(func=cmd_refresh)

    p_init = sub.add_parser("init", help="Enregistre la th\u00e8se initiale")
    p_init.add_argument("symbol")
    p_init.add_argument("thesis")
    p_init.add_argument("--criteria", nargs="*", help="Crit\u00e8res d'invalidation, un par argument")
    p_init.set_defaults(func=cmd_init)

    p_prompt = sub.add_parser("prompt", help="Affiche le prompt \u00e0 copier-coller")
    p_prompt.add_argument("symbol")
    p_prompt.set_defaults(func=cmd_prompt)

    p_ingest = sub.add_parser("ingest", help="Ing\u00e8re la r\u00e9ponse LLM coll\u00e9e dans un fichier")
    p_ingest.add_argument("symbol")
    p_ingest.add_argument("response_file")
    p_ingest.set_defaults(func=cmd_ingest)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
