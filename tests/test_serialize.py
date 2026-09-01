import json
from datetime import datetime, timedelta, timezone

import pytest

from src.registry import AssetRegistry
from src.schema import AssetKind, Platform, TransactionKind
from src.store.serialize import TX_STORE_VERSION, TxStore, load_tx_store, save_wallet

from tests.conftest import make_tx


# ---------------------------------------------------------------------------
# Round-trip save/load
# ---------------------------------------------------------------------------

def test_round_trip_preserves_transaction_fields(tmp_path, registry, t0):
    store = TxStore()
    tx = make_tx(registry, "BTC", TransactionKind.BUY, 0.5, 15000.0, t0, external_id="ext-1")
    store.add_transactions([tx], registry)

    path = tmp_path / "tx_store.json"
    save_wallet(store, path)
    reloaded = load_tx_store(path)

    assert len(reloaded.transactions) == 1
    got = reloaded.transactions[0]
    assert got.platform == Platform.BINANCE
    assert got.kind == TransactionKind.BUY
    assert got.quantity == 0.5
    assert got.value_eur == 15000.0
    assert got.external_id == "ext-1"
    assert got.time == t0
    assert reloaded.registry.get_asset(got.asset_id).symbol == "BTC"


def test_round_trip_is_idempotent_byte_for_byte(tmp_path, registry, t0):
    """Sauver, recharger, resauver doit produire un JSON strictement
    identique (hors `updated_at`) -- condition nécessaire pour un
    tx_store.json 'immutable' et pour des diffs git propres."""
    store = TxStore()
    tx1 = make_tx(registry, "BTC", TransactionKind.BUY, 0.5, 15000.0, t0, external_id="ext-1")
    tx2 = make_tx(registry, "ETH", TransactionKind.SELL, 2.0, 4000.0, t0 + timedelta(hours=1), external_id="ext-2")
    store.add_transactions([tx1, tx2], registry)

    path1 = tmp_path / "first.json"
    save_wallet(store, path1)

    reloaded = load_tx_store(path1)
    path2 = tmp_path / "second.json"
    save_wallet(reloaded, path2)

    data1 = json.loads(path1.read_text())
    data2 = json.loads(path2.read_text())
    del data1["updated_at"]
    del data2["updated_at"]
    assert data1 == data2


def test_load_missing_file_returns_empty_store(tmp_path):
    store = load_tx_store(tmp_path / "does_not_exist.json")
    assert store.transactions == []
    assert store.registry.get_all_assets() == []


def test_transactions_are_written_sorted_by_time(tmp_path, registry, t0):
    """save_wallet trie les transactions par 'time' -- vérifie que ça tient
    même quand elles sont ajoutées dans le désordre."""
    store = TxStore()
    tx_late = make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0 + timedelta(days=1), external_id="late")
    tx_early = make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0, external_id="early")
    store.add_transactions([tx_late, tx_early], registry)

    path = tmp_path / "tx_store.json"
    save_wallet(store, path)
    data = json.loads(path.read_text())

    times = [t["time"] for t in data["transactions"]]
    assert times == sorted(times)
    assert data["transactions"][0]["external_id"] == "early"


def test_saved_file_contains_version_and_assets(tmp_path, registry, t0):
    store = TxStore()
    tx = make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0, external_id="e1")
    store.add_transactions([tx], registry)

    path = tmp_path / "tx_store.json"
    save_wallet(store, path)
    data = json.loads(path.read_text())

    assert data["version"] == TX_STORE_VERSION
    assert "BTC" in data["assets"]
    assert data["assets"]["BTC"]["kind"] == AssetKind.CRYPTO.value


def test_time_serialized_as_utc_z_suffix(tmp_path, registry):
    """Les temps sont toujours réécrits en UTC avec suffixe 'Z', même si
    l'objet Transaction original avait un fuseau horaire différent."""
    tz_plus2 = timezone(timedelta(hours=2))
    local_time = datetime(2026, 6, 1, 14, 0, 0, tzinfo=tz_plus2)  # == 12:00 UTC
    store = TxStore()
    tx = make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, local_time, external_id="e1")
    store.add_transactions([tx], registry)

    path = tmp_path / "tx_store.json"
    save_wallet(store, path)
    data = json.loads(path.read_text())

    assert data["transactions"][0]["time"] == "2026-06-01T12:00:00Z"


# ---------------------------------------------------------------------------
# Dédoublonnage / fusion
# ---------------------------------------------------------------------------

def test_add_transactions_deduplicates_by_external_id(registry, t0):
    store = TxStore()
    tx = make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0, external_id="dup-1")
    added_first = store.add_transactions([tx], registry)
    added_second = store.add_transactions([tx], registry)

    assert added_first == 1
    assert added_second == 0
    assert len(store.transactions) == 1


def test_add_transactions_never_deduplicates_none_external_id(registry, t0):
    """external_id=None (ex: les FEE Binance) n'est jamais considéré comme
    doublon -- documente un choix potentiellement risqué : si un même
    fichier de fees est réimporté deux fois, chaque FEE sans external_id
    sera dupliqué. À surveiller si `cli.py` est ré-exécuté sur les mêmes
    fichiers bruts sans les déplacer/archiver après import."""
    store = TxStore()
    tx1 = make_tx(registry, "BNB", TransactionKind.FEE, 0.001, 0.3, t0, external_id=None)
    tx2 = make_tx(registry, "BNB", TransactionKind.FEE, 0.001, 0.3, t0, external_id=None)

    added = store.add_transactions([tx1, tx2], registry)
    assert added == 2
    assert len(store.transactions) == 2


def test_add_transactions_remaps_asset_ids_from_source_registry(t0):
    """Les asset_id du `source_registry` local à un run de parsing doivent
    être retraduits via le symbole vers les ids du registre persistant --
    ici volontairement différents pour s'assurer que la traduction a bien
    lieu (et pas juste une coïncidence car `_stable_asset_id` est
    déterministe)."""
    source_registry = AssetRegistry()
    tx = make_tx(source_registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0, external_id="e1")

    store = TxStore()
    store.add_transactions([tx], source_registry)

    stored_tx = store.transactions[0]
    assert store.registry.get_asset(stored_tx.asset_id).symbol == "BTC"
    # Le TxStore a bien créé SA PROPRE entrée de registre (pas de partage
    # d'instance avec source_registry).
    assert store.registry is not source_registry


def test_reimporting_same_file_twice_yields_no_duplicates(tmp_path, registry, t0):
    """Scénario cli.py réel : deux runs successifs sur les mêmes fichiers
    d'export ne doivent pas faire grossir le tx_store.json."""
    path = tmp_path / "tx_store.json"

    store1 = TxStore()
    tx = make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0, external_id="stable-id")
    store1.add_transactions([tx], registry)
    save_wallet(store1, path)

    # Deuxième run : on recharge, reparse le même fichier source (même
    # transaction, même external_id), et refusionne.
    store2 = load_tx_store(path)
    registry2 = AssetRegistry()
    tx_again = make_tx(registry2, "BTC", TransactionKind.BUY, 1.0, 100.0, t0, external_id="stable-id")
    added = store2.add_transactions([tx_again], registry2)
    save_wallet(store2, path)

    assert added == 0
    data = json.loads(path.read_text())
    assert len(data["transactions"]) == 1


# ---------------------------------------------------------------------------
# Robustesse du chargement (fichiers malformés / partiels)
# ---------------------------------------------------------------------------

def test_load_raises_on_invalid_json(tmp_path):
    path = tmp_path / "tx_store.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_tx_store(path)


def test_load_raises_keyerror_when_asset_referenced_but_missing_from_assets_meta(tmp_path):
    """Un tx_store.json corrompu à la main (ou par un bug d'un futur format
    de migration) référence un symbole absent de la section 'assets' :
    `_transaction_from_dict` lève un KeyError peu explicite. Documente un
    point à durcir avant de qualifier le format 'immutable' -- un message
    d'erreur clair (voire une validation de schéma au chargement) éviterait
    un stacktrace obscur en prod."""
    path = tmp_path / "tx_store.json"
    payload = {
        "version": 1,
        "updated_at": "2026-01-01T00:00:00Z",
        "assets": {},
        "transactions": [{
            "platform": "Binance", "account_label": "Spot", "kind": "Buy",
            "asset": "BTC", "quantity": 1.0, "price": None, "value_eur": 100.0,
            "amount": None, "quote_currency": None, "time": "2026-01-01T00:00:00Z",
            "external_id": "e1", "remark": None, "source_file": "test",
        }],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(KeyError):
        load_tx_store(path)


def test_load_raises_on_missing_required_transaction_field(tmp_path):
    """Un champ requis manquant (ex: 'quantity' supprimé par une édition
    manuelle du JSON) doit faire échouer le chargement plutôt que de
    produire un Wallet à moitié cohérent."""
    path = tmp_path / "tx_store.json"
    payload = {
        "version": 1,
        "updated_at": "2026-01-01T00:00:00Z",
        "assets": {"BTC": {"name": "BTC", "kind": "Crypto", "ref_currency": "USD",
                            "identifiers": {"isin": None, "ticker": None}}},
        "transactions": [{
            "platform": "Binance", "account_label": "Spot", "kind": "Buy",
            "asset": "BTC", "price": None, "value_eur": 100.0,
            "amount": None, "quote_currency": None, "time": "2026-01-01T00:00:00Z",
            "external_id": "e1", "remark": None, "source_file": "test",
            # "quantity" manquant volontairement
        }],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(KeyError):
        load_tx_store(path)


def test_save_creates_parent_directories(tmp_path, registry, t0):
    nested_path = tmp_path / "a" / "b" / "tx_store.json"
    store = TxStore()
    tx = make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0, external_id="e1")
    store.add_transactions([tx], registry)
    save_wallet(store, nested_path)
    assert nested_path.exists()


def test_save_is_atomic_enough_to_not_leave_partial_file_on_success(tmp_path, registry, t0):
    """save_wallet réécrit le fichier entier -- vérifie qu'un save réussi
    est toujours un JSON complet et valide (pas de troncature)."""
    store = TxStore()
    tx = make_tx(registry, "BTC", TransactionKind.BUY, 1.0, 100.0, t0, external_id="e1")
    store.add_transactions([tx], registry)
    path = tmp_path / "tx_store.json"
    save_wallet(store, path)
    # Doit être parseable sans erreur.
    json.loads(path.read_text())
