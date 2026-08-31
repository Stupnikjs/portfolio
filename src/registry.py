import hashlib
from typing import Dict

from .schema import Asset, AssetIdentifiers, AssetKind


def _stable_asset_id(symbol: str) -> int:
    """ID déterministe dérivé du symbole -- le même symbole produit
    toujours le même id, indépendamment de l'ordre de parsing ou du run.

    Ça élimine le besoin de remapper les asset_id d'un registre local
    (créé à chaque exécution de cli.py) vers le registre persistant du
    wallet : `find_or_create()` sur n'importe quel registre -- local à
    un run, ou celui rechargé depuis wallet.json -- attribue le même id
    au même symbole, donc `wallet.add_transactions()` peut fusionner
    directement sans traduction d'ids.
    """
    digest = hashlib.sha256(symbol.encode("utf-8")).hexdigest()
    return int(digest[:15], 16)  # 60 bits -- collision négligeable pour un nombre de symboles réaliste


class AssetRegistry:
    def __init__(self):
        self._assets: Dict[int, Asset] = {}
        self._symbol_to_id: Dict[str, int] = {}

    def find_or_create(self, symbol: str, name: str, kind: AssetKind, ref_currency: str, identifiers: AssetIdentifiers) -> int:
        if symbol in self._symbol_to_id:
            return self._symbol_to_id[symbol]

        asset_id = _stable_asset_id(symbol)
        existing = self._assets.get(asset_id)
        if existing is not None and existing.symbol != symbol:
            # Collision sha256 tronquée à 60 bits : astronomiquement
            # improbable pour un nombre de symboles réaliste (~2^60
            # valeurs possibles), mais on préfère planter bruyamment
            # plutôt que corrompre silencieusement un actif existant.
            raise ValueError(
                f"Collision d'id entre '{symbol}' et '{existing.symbol}' (id={asset_id})"
            )

        self._assets[asset_id] = Asset(
            id=asset_id, symbol=symbol, name=name, kind=kind,
            ref_currency=ref_currency, identifiers=identifiers
        )
        self._symbol_to_id[symbol] = asset_id
        return asset_id

    def get_all_assets(self):
        return list(self._assets.values())

    def get_asset(self, asset_id: int) -> Asset:
        """Lookup par id -- nécessaire pour retrouver le symbole stable
        d'une Transaction lors de la sérialisation vers wallet.json."""
        return self._assets[asset_id]
