import pytest

from src.registry import AssetRegistry, _stable_asset_id
from src.schema import AssetIdentifiers, AssetKind


def test_find_or_create_is_deterministic_across_instances():
    """Deux registres indépendants (ex: un registre `source_registry` de
    run de parsing, et le registre persistant rechargé du wallet) doivent
    attribuer le même id au même symbole -- c'est ce qui permet à
    `TxStore.add_transactions` de fusionner sans table de correspondance."""
    r1 = AssetRegistry()
    r2 = AssetRegistry()
    id1 = r1.find_or_create("BTC", "Bitcoin", AssetKind.CRYPTO, "USD", AssetIdentifiers())
    id2 = r2.find_or_create("BTC", "Bitcoin", AssetKind.CRYPTO, "USD", AssetIdentifiers())
    assert id1 == id2 == _stable_asset_id("BTC")


def test_find_or_create_returns_same_id_for_same_symbol():
    r = AssetRegistry()
    id1 = r.find_or_create("ETH", "Ethereum", AssetKind.CRYPTO, "USD", AssetIdentifiers())
    id2 = r.find_or_create("ETH", "Ethereum", AssetKind.CRYPTO, "USD", AssetIdentifiers())
    assert id1 == id2
    assert len(r.get_all_assets()) == 1


def test_find_or_create_different_symbols_get_different_ids():
    r = AssetRegistry()
    id_btc = r.find_or_create("BTC", "Bitcoin", AssetKind.CRYPTO, "USD", AssetIdentifiers())
    id_eth = r.find_or_create("ETH", "Ethereum", AssetKind.CRYPTO, "USD", AssetIdentifiers())
    assert id_btc != id_eth


def test_get_asset_unknown_id_raises_keyerror():
    r = AssetRegistry()
    with pytest.raises(KeyError):
        r.get_asset(999999)


def test_find_or_create_silently_keeps_first_metadata_on_conflicting_calls():
    """ROBUSTESSE : si le même symbole est réenregistré avec des métadonnées
    différentes (ex: `kind` ou `ref_currency` divergents entre deux sources,
    ou une correction de `name`), `find_or_create` retourne l'id existant
    SANS mettre à jour l'Asset ni signaler quoi que ce soit. C'est un piège
    silencieux : si Binance et XTB utilisaient un jour le même symbole avec
    des `ref_currency` différentes, la deuxième valeur serait perdue sans
    avertissement. Ce test documente le comportement actuel ; il devrait
    échouer (et donc être corrigé côté source) si on ajoute une validation
    de cohérence dans `find_or_create`.
    """
    r = AssetRegistry()
    r.find_or_create("XYZ", "XYZ Corp", AssetKind.STOCK, "USD", AssetIdentifiers())
    r.find_or_create("XYZ", "XYZ Corp (renamed)", AssetKind.STOCK, "EUR", AssetIdentifiers())

    asset = r.get_asset(_stable_asset_id("XYZ"))
    assert asset.name == "XYZ Corp"          # la 2e valeur ("renamed") est perdue
    assert asset.ref_currency == "USD"       # idem pour "EUR"


def test_collision_detection_raises_when_ids_collide_for_different_symbols(monkeypatch):
    """Le code prévoit explicitement un plantage bruyant en cas de collision
    d'id (60 bits) entre deux symboles différents plutôt qu'une corruption
    silencieuse -- on le vérifie en forçant artificiellement une collision."""
    import src.registry as registry_mod

    monkeypatch.setattr(registry_mod, "_stable_asset_id", lambda symbol: 42)
    r = AssetRegistry()
    r.find_or_create("AAA", "AAA", AssetKind.CRYPTO, "USD", AssetIdentifiers())
    with pytest.raises(ValueError, match="Collision"):
        r.find_or_create("BBB", "BBB", AssetKind.CRYPTO, "USD", AssetIdentifiers())
