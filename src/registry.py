from .schema import Asset, AssetIdentifiers, AssetKind
from typing import Dict

class AssetRegistry:
    def __init__(self):
        self._assets: Dict[int, Asset] = {}
        self._symbol_to_id: Dict[str, int] = {}
        self._next_id = 1

    def find_or_create(self, symbol: str, name: str, kind: AssetKind, ref_currency: str, identifiers: AssetIdentifiers) -> int:
        if symbol in self._symbol_to_id:
            return self._symbol_to_id[symbol]
        
        asset_id = self._next_id
        self._assets[asset_id] = Asset(
            id=asset_id, symbol=symbol, name=name, kind=kind, 
            ref_currency=ref_currency, identifiers=identifiers
        )
        self._symbol_to_id[symbol] = asset_id
        self._next_id += 1
        return asset_id

    def get_all_assets(self):
        return list(self._assets.values())

    def get_asset(self, asset_id: int) -> Asset:
        """Lookup par id -- nécessaire pour retrouver le symbole stable
        d'une Transaction lors de la sérialisation vers wallet.json."""
        return self._assets[asset_id]