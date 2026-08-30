"""Équivalent Python de pf_extract::binance (parse_trades, parse_converts)."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from pathlib import Path

from .prices import historical_price_eur
from .registry import AssetRegistry
from .schema import AssetIdentifiers, AssetKind, Platform, Transaction, TransactionKind

_AMOUNT_RE = re.compile(r"^([0-9.]+)([A-Za-z]+)$")

def _split_amount(raw: str) -> tuple[float, str]:
    """Sépare une cellule collée '<nombre><symbole>' (format Trade History)."""
    match = _AMOUNT_RE.match(raw.strip())
    if not match:
        raise ValueError(f"pas de suffixe trouvé dans '{raw}'")
    qty, symbol = match.groups()
    return float(qty), symbol


def _split_space_amount(raw: str) -> tuple[float, str]:
    """Sépare une cellule '<nombre> <symbole>' (format Convert), à ne pas
    confondre avec `_split_amount` (collé, format Trade History)."""
    parts = raw.strip().split(" ", 1)
    if len(parts) != 2:
        raise ValueError(f"pas de symbole dans '{raw}'")
    qty_str, symbol = parts
    return float(qty_str), symbol


def _normalize_currency(coin: str) -> str | None:
    if coin in ("EUR", "EURI"):
        return "EUR"
    if coin in ("USDC", "USDT"):
        return "USD"
    return None


def _asset_kind_for(symbol: str) -> AssetKind:
    return AssetKind.CASH if _normalize_currency(symbol) is not None else AssetKind.CRYPTO


def parse_trades(path: Path, registry: AssetRegistry) -> list[Transaction]:
    """Parse un export Binance 'Trade History' en transactions Buy/Sell + Fee.

    Seule source Binance retenue -- le format 'Account Statement' est abandonné
    (pas de prix d'exécution fiable, appariement heuristique trop fragile).
    """
    raw_content = path.read_text(encoding="utf-8-sig")
    source_file = str(path)
    out: list[Transaction] = []

    reader = csv.DictReader(io.StringIO(raw_content))
    for row in reader:
        time = datetime.strptime(row["Time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

        base_qty, base_symbol = _split_amount(row["Executed"])
        quote_amount, quote_symbol = _split_amount(row["Amount"])
        fee_amount, fee_symbol = _split_amount(row["Fee"])

        side = row["Side"].upper()
        if side == "BUY":
            kind = TransactionKind.BUY
        elif side == "SELL":
            kind = TransactionKind.SELL
        else:
            raise ValueError(f"side inconnu: {side}")

        base_ref_currency = _normalize_currency(base_symbol) or "USD"
        base_asset_id = registry.find_or_create(
            base_symbol, base_symbol, _asset_kind_for(base_symbol),
            base_ref_currency, AssetIdentifiers(),
        )

        quote_currency = _normalize_currency(quote_symbol) or quote_symbol
        eur_price = historical_price_eur(base_symbol, time)

        out.append(Transaction(
            platform=Platform.BINANCE,
            account_label="Spot",
            kind=kind,
            asset_id=base_asset_id,
            quantity=base_qty,
            price=eur_price,
            amount=quote_amount,
            quote_currency=quote_currency,
            time=time,
            external_id=None,
            remark=None,
            source_file=source_file,
        ))

        if fee_amount > 0.0:
            fee_ref_currency = _normalize_currency(fee_symbol) or "USD"
            fee_asset_id = registry.find_or_create(
                fee_symbol, fee_symbol, _asset_kind_for(fee_symbol),
                fee_ref_currency, AssetIdentifiers(),
            )
            out.append(Transaction(
                platform=Platform.BINANCE,
                account_label="Spot",
                kind=TransactionKind.FEE,
                asset_id=fee_asset_id,
                quantity=fee_amount,
                price=eur_price,
                amount=None,
                quote_currency=None,
                time=time,
                external_id=None,
                remark=f"Fee on {row['Side']} {base_symbol}",
                source_file=source_file,
            ))

    return out


def parse_converts(path: Path, registry: AssetRegistry) -> list[Transaction]:
    """Parse un export Binance 'Convert History'. Chaque ligne réussie devient
    deux transactions (Sell de l'actif cédé, Buy de l'actif reçu) -- les
    conversions échouées/annulées (Status != 'Successful') sont ignorées.
    """
    raw_content = path.read_text(encoding="utf-8-sig")
    source_file = str(path)
    out: list[Transaction] = []

    reader = csv.DictReader(io.StringIO(raw_content))
    for row in reader:
        if row["Status"] != "Successful":
            continue

        time = datetime.strptime(row["Time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        sell_qty, sell_symbol = _split_space_amount(row["Sell"])
        buy_qty, buy_symbol = _split_space_amount(row["Buy"])

        sell_asset_id = registry.find_or_create(
            sell_symbol, sell_symbol, _asset_kind_for(sell_symbol),
            _normalize_currency(sell_symbol) or "USD", AssetIdentifiers(),
        )
        buy_asset_id = registry.find_or_create(
            buy_symbol, buy_symbol, _asset_kind_for(buy_symbol),
            _normalize_currency(buy_symbol) or "USD", AssetIdentifiers(),
        )

        sell_price_eur = historical_price_eur(sell_symbol, time)
        buy_price_eur = historical_price_eur(buy_symbol, time)
        convert_value_eur = sell_qty * sell_price_eur

        out.append(Transaction(
            platform=Platform.BINANCE,
            account_label=row["Wallet"],
            kind=TransactionKind.SELL,
            asset_id=sell_asset_id,
            quantity=sell_qty,
            price=sell_price_eur,
            amount=convert_value_eur,
            quote_currency="EUR",
            time=time,
            external_id=None,
            remark="Convert",
            source_file=source_file,
        ))
        out.append(Transaction(
            platform=Platform.BINANCE,
            account_label=row["Wallet"],
            kind=TransactionKind.BUY,
            asset_id=buy_asset_id,
            quantity=buy_qty,
            price=buy_price_eur,
            amount=convert_value_eur,
            quote_currency="EUR",
            time=time,
            external_id=None,
            remark="Convert",
            source_file=source_file,
        ))

    return out