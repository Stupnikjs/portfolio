from src.registry import _stable_asset_id
from src.schema import AssetKind, _asset_id


def test_schema_asset_id_and_registry_asset_id_diverge():
    """`schema._asset_id` (triplet symbol+kind+ref_currency) et
    `registry._stable_asset_id` (symbole seul) sont deux fonctions de
    hachage DIFFERENTES qui coexistent dans le code. Seule celle de
    `registry.py` est réellement utilisée par `AssetRegistry`.
    `schema._asset_id` semble être du code mort, ou un vestige d'une
    version antérieure -- ce test documente l'écart pour éviter qu'on le
    redécouvre en debug de prod. Si le schéma final doit garder
    `schema._asset_id`, il faut brancher `AssetRegistry` dessus (et donc
    lui passer kind/ref_currency), sinon le supprimer.
    """
    a = _asset_id("BTC", AssetKind.CRYPTO, "USD")
    b = _stable_asset_id("BTC")
    assert a != b
