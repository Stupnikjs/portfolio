from datetime import datetime, timezone

import openpyxl
import pytest

from src.parse import xtb
from src.registry import AssetRegistry


def _make_closed_workbook(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CLOSED POSITION HISTORY"
    # Lignes de titre/résumé de compte parasites au-dessus du vrai tableau,
    # comme dans un export XTB réel (colonne A vide).
    ws.append([None, "Some account summary line"])
    ws.append([None, None])
    # En-tête (ligne "colonne Position n'est pas un nombre" -> ignorée)
    ws.append([None, "Position", "Symbol", "Type", "Volume", "Open time", "Open price",
               "Close time", "Close price", "Open origin", "Close origin",
               "Purchase value", "Sale value", "S/L", "T/P", "Margin",
               "Commission", "Swap", "Rollover", "Gross P/L"])
    ws.append([None, 12345, "CDR.PL", "BUY", 10, "01/06/2026 09:00:00", 100.0,
               "02/06/2026 09:00:00", 110.0, "Client", "Client",
               1000.0, 1100.0, None, None, None, -1.0, 0.0, 0.0, 100.0])
    # Ligne "Total" en pied de tableau : colonne Position vide -> ignorée.
    ws.append([None, "Total", None, None, None, None, None, None, None, None,
               None, None, None, None, None, None, None, None, None, None])
    wb.save(path)


def _make_open_workbook(path, sheet_name="OPEN POSITION 01062026"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(["Position", "Symbol", "Type", "Volume", "Open time", "Open price",
               "Market price", "Purchase value", "S/L", "T/P", "Margin",
               "Commission", "Swap", "Rollover", "Gross P/L", "Comment"])
    ws.append([54321, "AAPL.US", "BUY", 5, "01/06/2026 09:00:00", 150.0,
               160.0, 750.0, None, None, None, -0.5, 0.0, 0.0, 50.0, "note"])
    wb.save(path)


def test_find_sheet_by_prefix_matches(tmp_path):
    path = tmp_path / "account.xlsx"
    _make_closed_workbook(path)
    name = xtb.find_sheet_by_prefix(path, "CLOSED POSITION")
    assert name == "CLOSED POSITION HISTORY"


def test_find_sheet_by_prefix_raises_when_absent(tmp_path):
    path = tmp_path / "account.xlsx"
    _make_closed_workbook(path)
    with pytest.raises(ValueError, match="aucun onglet"):
        xtb.find_sheet_by_prefix(path, "OPEN POSITION")


def test_parse_closed_positions_skips_header_and_total_rows(tmp_path):
    path = tmp_path / "account.xlsx"
    _make_closed_workbook(path)
    positions = xtb.parse_closed_positions(path, "CLOSED POSITION HISTORY")

    assert len(positions) == 1
    pos = positions[0]
    assert pos.position_id == "12345"
    assert pos.symbol == "CDR.PL"
    assert pos.volume == 10
    assert pos.purchase_value == 1000.0
    assert pos.sale_value == 1100.0
    assert pos.open_time == datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)


def test_closed_position_to_transactions_produces_buy_and_sell(tmp_path):
    path = tmp_path / "account.xlsx"
    _make_closed_workbook(path)
    positions = xtb.parse_closed_positions(path, "CLOSED POSITION HISTORY")
    registry = AssetRegistry()

    txs = positions[0].to_transactions(registry)
    assert len(txs) == 2
    buy, sell = txs
    assert buy.external_id == "12345-buy"
    assert sell.external_id == "12345-sell"
    assert buy.value_eur == 1000.0
    assert sell.value_eur == 1100.0
    # CDR.PL -> suffixe "PL" absent de la table de correspondance -> EUR par défaut
    assert registry.get_asset(buy.asset_id).ref_currency == "EUR"


def test_parse_open_positions_reads_rows_after_header(tmp_path):
    path = tmp_path / "account.xlsx"
    _make_open_workbook(path)
    positions = xtb.parse_open_positions(path, "OPEN POSITION 01062026")

    assert len(positions) == 1
    pos = positions[0]
    assert pos.position_id == "54321"
    assert pos.symbol == "AAPL.US"
    assert pos.comment == "note"


def test_open_position_to_transaction_infers_usd_currency(tmp_path):
    path = tmp_path / "account.xlsx"
    _make_open_workbook(path)
    positions = xtb.parse_open_positions(path, "OPEN POSITION 01062026")
    registry = AssetRegistry()

    tx = positions[0].to_transaction(registry)
    assert tx.external_id == "54321"
    assert registry.get_asset(tx.asset_id).ref_currency == "USD"  # suffixe .US


def test_infer_currency_defaults_to_eur_for_unknown_suffix():
    assert xtb._infer_currency("XYZ.ZZ") == "EUR"
    assert xtb._infer_currency("NOSUFFIX") == "EUR"


def test_cell_datetime_parses_string_and_native_datetime():
    assert xtb._cell_datetime("01/06/2026 09:00:00") == datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
    naive = datetime(2026, 6, 1, 9, 0, 0)
    assert xtb._cell_datetime(naive).tzinfo is not None


def test_cell_datetime_raises_on_unexpected_type():
    with pytest.raises(ValueError):
        xtb._cell_datetime(12345)


def test_cell_f64_returns_none_on_non_numeric():
    assert xtb._cell_f64("not a number") is None
    assert xtb._cell_f64(None) is None
    assert xtb._cell_f64("42.5") == 42.5
