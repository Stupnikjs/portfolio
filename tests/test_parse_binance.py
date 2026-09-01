import pytest

from src.parse import binance
from src.registry import AssetRegistry
from src.schema import TransactionKind


@pytest.fixture(autouse=True)
def no_network_prices(monkeypatch):
    """Empêche tout appel réseau réel : tous les tests de ce fichier
    doivent passer hors-ligne. Prix fixe et prévisible pour les assertions."""
    monkeypatch.setattr(binance, "historical_price_eur", lambda symbol, time: 100.0)


TRADES_CSV = (
    "Date(UTC)\tPair\tSide\tPrice\tExecuted\tAmount\tFee\n"
).replace("\t", ",")

# En-têtes réels attendus par le parseur (voir row["Time"], row["Pair"], ...)
TRADES_HEADER = "Time,Pair,Side,Price,Executed,Amount,Fee"


def _write(path, content):
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_trades_buy_and_fee(tmp_path):
    csv_content = (
        f"{TRADES_HEADER}\n"
        "2026-01-01 10:00:00,BTCUSDT,BUY,20000,0.10000000BTC,2000.00000000USDT,0.00010000BNB\n"
    )
    path = _write(tmp_path / "trades.csv", csv_content)
    registry = AssetRegistry()

    txs = binance.parse_trades(path, registry)

    # 1 BUY (BTC) + 1 FEE (BNB)
    assert len(txs) == 2
    buy = next(t for t in txs if t.kind == TransactionKind.BUY)
    fee = next(t for t in txs if t.kind == TransactionKind.FEE)

    assert buy.quantity == pytest.approx(0.1)
    assert buy.value_eur == pytest.approx(0.1 * 100.0)
    assert registry.get_asset(buy.asset_id).symbol == "BTC"

    assert fee.quantity == pytest.approx(0.0001)
    assert registry.get_asset(fee.asset_id).symbol == "BNB"
    assert fee.remark == "Fee on BUY BTC"


def test_parse_trades_sell_without_fee(tmp_path):
    csv_content = (
        f"{TRADES_HEADER}\n"
        "2026-01-01 10:00:00,BTCUSDT,SELL,20000,0.10000000BTC,2000.00000000USDT,0.00000000USDT\n"
    )
    path = _write(tmp_path / "trades.csv", csv_content)
    registry = AssetRegistry()

    txs = binance.parse_trades(path, registry)
    # fee_amount == 0.0 -> pas de transaction FEE ajoutée
    assert len(txs) == 1
    assert txs[0].kind == TransactionKind.SELL


def test_parse_trades_unknown_side_raises(tmp_path):
    csv_content = (
        f"{TRADES_HEADER}\n"
        "2026-01-01 10:00:00,BTCUSDT,HOLD,20000,0.1BTC,2000.0USDT,0.0USDT\n"
    )
    path = _write(tmp_path / "trades.csv", csv_content)
    with pytest.raises(ValueError, match="side inconnu"):
        binance.parse_trades(path, AssetRegistry())


def test_parse_trades_generates_stable_external_id_across_reparse(tmp_path):
    """Reparser le même fichier doit donner le même external_id -- c'est
    la garantie utilisée par TxStore pour dédupliquer un réimport."""
    csv_content = (
        f"{TRADES_HEADER}\n"
        "2026-01-01 10:00:00,BTCUSDT,BUY,20000,0.1BTC,2000.0USDT,0.0USDT\n"
    )
    path = _write(tmp_path / "trades.csv", csv_content)

    txs1 = binance.parse_trades(path, AssetRegistry())
    txs2 = binance.parse_trades(path, AssetRegistry())

    assert txs1[0].external_id == txs2[0].external_id


def test_parse_converts_creates_sell_and_buy_pair(tmp_path):
    csv_content = (
        "Time,Wallet,Pair,Sell,Buy,Price,Status\n"
        "2026-01-01 10:00:00,Spot,BTC/ETH,0.1 BTC,1.5 ETH,15,Successful\n"
    )
    path = _write(tmp_path / "convert.csv", csv_content)
    registry = AssetRegistry()

    txs = binance.parse_converts(path, registry)
    assert len(txs) == 2
    sell = next(t for t in txs if t.kind == TransactionKind.SELL)
    buy = next(t for t in txs if t.kind == TransactionKind.BUY)
    assert sell.external_id.endswith("-sell")
    assert buy.external_id.endswith("-buy")
    assert sell.external_id[:-5] == buy.external_id[:-4]  # même préfixe convert_id


def test_parse_converts_skips_non_successful(tmp_path):
    csv_content = (
        "Time,Wallet,Pair,Sell,Buy,Price,Status\n"
        "2026-01-01 10:00:00,Spot,BTC/ETH,0.1 BTC,1.5 ETH,15,Failed\n"
    )
    path = _write(tmp_path / "convert.csv", csv_content)
    txs = binance.parse_converts(path, AssetRegistry())
    assert txs == []


def test_split_amount_requires_suffix():
    with pytest.raises(ValueError):
        binance._split_amount("12345")


def test_split_space_amount_requires_two_parts():
    with pytest.raises(ValueError):
        binance._split_space_amount("12345")


@pytest.mark.parametrize("coin,expected", [
    ("EUR", "EUR"),
    ("EURI", "EUR"),
    ("USDC", "USD"),
    ("USDT", "USD"),
    ("BTC", None),
])
def test_normalize_currency(coin, expected):
    assert binance._normalize_currency(coin) == expected
