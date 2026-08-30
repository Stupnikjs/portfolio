"""Équivalent Python de pf_extract::xtb (positions ouvertes/fermées XTB)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import openpyxl

from ..registry import AssetRegistry
from ..schema import AssetIdentifiers, AssetKind, Platform, Transaction, TransactionKind


@dataclass
class XtbClosedPosition:
    position_id: str
    symbol: str
    side: str
    volume: float
    open_time: datetime
    open_price: float
    close_time: datetime
    close_price: float
    open_origin: str
    close_origin: str
    purchase_value: float
    sale_value: float
    sl: Optional[float]
    tp: Optional[float]
    margin: Optional[float]
    commission: float
    swap: float
    rollover: float
    gross_pl: float
    source_file: str

    def to_transactions(self, registry: AssetRegistry) -> list[Transaction]:
        currency = _infer_currency(self.symbol)
        asset_id = registry.find_or_create(
            self.symbol, self.symbol, AssetKind.STOCK, currency, AssetIdentifiers(),
        )
        return [
            Transaction(
                platform=Platform.XTB, account_label="XTB", kind=TransactionKind.BUY,
                asset_id=asset_id, quantity=self.volume, price=self.open_price,
                amount=self.purchase_value, quote_currency=None, time=self.open_time,
                value_eur=self.purchase_value,
                external_id=self.position_id, remark=None, source_file=self.source_file,
            ),
            Transaction(
                platform=Platform.XTB, account_label="XTB", kind=TransactionKind.SELL,
                asset_id=asset_id, quantity=self.volume, price=self.close_price,
                amount=self.sale_value, quote_currency=None, time=self.close_time,
                value_eur=self.sale_value,
                external_id=self.position_id, remark=None, source_file=self.source_file,
            ),
        ]


@dataclass
class XtbOpenPosition:
    position_id: str
    symbol: str
    side: str
    volume: float
    open_time: datetime
    open_price: float
    market_price: float
    purchase_value: float
    sl: Optional[float]
    tp: Optional[float]
    margin: Optional[float]
    commission: float
    swap: float
    rollover: float
    gross_pl: float
    comment: Optional[str]
    source_file: str

    def to_transaction(self, registry: AssetRegistry) -> Transaction:
        currency = _infer_currency(self.symbol)
        asset_id = registry.find_or_create(
            self.symbol, self.symbol, AssetKind.STOCK, currency, AssetIdentifiers(),
        )
        return Transaction(
            platform=Platform.XTB, account_label="XTB", kind=TransactionKind.BUY,
            asset_id=asset_id, quantity=self.volume, price=self.open_price,
            amount=self.purchase_value, quote_currency=None, time=self.open_time,
            value_eur=self.purchase_value,
            external_id=self.position_id, remark=self.comment, source_file=self.source_file,
        )


def _infer_currency(symbol: str) -> str:
    suffix = symbol.rsplit(".", 1)[-1] if "." in symbol else ""
    return {
        "DE": "EUR", "NL": "EUR", "FR": "EUR", "ES": "EUR", "IT": "EUR",
        "UK": "GBP", "US": "USD",
    }.get(suffix, "EUR")


def find_sheet_by_prefix(path: Path, prefix: str) -> str:
    """Trouve dynamiquement le nom d'onglet commençant par un préfixe donné,
    utile pour 'OPEN POSITION <date>' dont le nom exact change à chaque export.
    """
    wb = openpyxl.load_workbook(path, read_only=True)
    try:
        for name in wb.sheetnames:
            if name.startswith(prefix):
                return name
    finally:
        wb.close()
    raise ValueError(f"aucun onglet commençant par '{prefix}'")


def _cell_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _cell_f64(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cell_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        naive = datetime.strptime(value.strip(), "%d/%m/%Y %H:%M:%S")
        return naive.replace(tzinfo=timezone.utc)
    raise ValueError(f"format de date inattendu: {value!r}")


def parse_closed_positions(path: Path, sheet_name: str) -> list[XtbClosedPosition]:
    """Parse l'onglet 'Closed Position History' d'un export XTB xlsx.

    NB: pas de `read_only=True` ici -- openpyxl s'appuie en mode read_only sur
    la balise `<dimension>` du XML pour savoir quelle plage lire, et les
    exports XTB ont cette balise absente/incorrecte (symptôme observé :
    iter_rows ne renvoie que des tuples vides). Le mode normal l'ignore et lit
    vraiment la feuille.
    """
    source_file = str(path)
    wb = openpyxl.load_workbook(path, read_only=False, data_only=True)
    try:
        sheet = wb[sheet_name]
        out: list[XtbClosedPosition] = []

        # Pas de `next(rows, None)` pour sauter un en-tête fixe : les exports
        # XTB ont un nombre variable de lignes de titre/résumé de compte
        # au-dessus du vrai tableau (colonne A vide -> décalage d'index +1
        # sur toutes les colonnes). On ignore simplement toute ligne dont la
        # colonne "Position" (row[1]) n'est pas un nombre -- ça élimine à la
        # fois les lignes de titre, la ligne d'en-tête et la ligne "Total".
        for row in sheet.iter_rows(values_only=True):
            position_id = _cell_f64(row[1])
            if position_id is None:
                continue

            out.append(XtbClosedPosition(
                position_id=str(int(position_id)),
                symbol=_cell_str(row[2]),
                side=_cell_str(row[3]),
                volume=_cell_f64(row[4]) or 0.0,
                open_time=_cell_datetime(row[5]),
                open_price=_cell_f64(row[6]) or 0.0,
                close_time=_cell_datetime(row[7]),
                close_price=_cell_f64(row[8]) or 0.0,
                open_origin=_cell_str(row[9]),
                close_origin=_cell_str(row[10]),
                purchase_value=_cell_f64(row[11]) or 0.0,
                sale_value=_cell_f64(row[12]) or 0.0,
                sl=_cell_f64(row[13]),
                tp=_cell_f64(row[14]),
                margin=_cell_f64(row[15]),
                commission=_cell_f64(row[16]) or 0.0,
                swap=_cell_f64(row[17]) or 0.0,
                rollover=_cell_f64(row[18]) or 0.0,
                gross_pl=_cell_f64(row[19]) or 0.0,
                source_file=source_file,
            ))
        return out
    finally:
        wb.close()


def parse_open_positions(path: Path, sheet_name: str) -> list[XtbOpenPosition]:
    """Parse l'onglet 'OPEN POSITION <date>' d'un export XTB xlsx.
    Le nom de l'onglet inclut une date qui change à chaque export
    (ex: 'OPEN POSITION 29072026'), donc `sheet_name` doit être fourni exactement.

    Voir la note dans `parse_closed_positions` : pas de `read_only=True`.
    """
    source_file = str(path)
    wb = openpyxl.load_workbook(path, read_only=False, data_only=True)
    try:
        sheet = wb[sheet_name]
        rows = sheet.iter_rows(values_only=True)
        next(rows, None)  # en-tête
        out: list[XtbOpenPosition] = []

        for row in rows:
            position_id = _cell_f64(row[0])
            if position_id is None:
                continue
            if position_id == 0.0 and row[1] is None:
                continue

            comment = _cell_str(row[15]) if len(row) > 15 else ""
            comment = comment or None

            out.append(XtbOpenPosition(
                position_id=str(int(position_id)),
                symbol=_cell_str(row[1]),
                side=_cell_str(row[2]),
                volume=_cell_f64(row[3]) or 0.0,
                open_time=_cell_datetime(row[4]),
                open_price=_cell_f64(row[5]) or 0.0,
                market_price=_cell_f64(row[6]) or 0.0,
                purchase_value=_cell_f64(row[7]) or 0.0,
                sl=_cell_f64(row[8]),
                tp=_cell_f64(row[9]),
                margin=_cell_f64(row[10]),
                commission=_cell_f64(row[11]) or 0.0,
                swap=_cell_f64(row[12]) or 0.0,
                rollover=_cell_f64(row[13]) or 0.0,
                gross_pl=_cell_f64(row[14]) or 0.0,
                comment=comment,
                source_file=source_file,
            ))
        return out
    finally:
        wb.close()