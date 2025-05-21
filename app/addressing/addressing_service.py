from typing import Protocol

import inject

from app.addressing.models import ZalSearchResponseEntry


class AddressingAdapter(Protocol):
    def search_by_medmij_name(self, name: str) -> ZalSearchResponseEntry | None: ...

    def search_by_ura(self, ura: str) -> ZalSearchResponseEntry | None: ...

    def search_by_agb(self, agb: str) -> ZalSearchResponseEntry | None: ...

    def search_by_hrn(self, hrn: str) -> ZalSearchResponseEntry | None: ...

    def search_by_kvk(arg, kvk: str) -> ZalSearchResponseEntry | None: ...


class AddressingService:
    @inject.autoparams()
    def __init__(self, adapter: AddressingAdapter):
        self.adapter: AddressingAdapter = adapter

    def search_by_medmij_name(self, name: str) -> ZalSearchResponseEntry | None:
        return self.adapter.search_by_medmij_name(name)

    def search_by_ura(self, ura: str) -> ZalSearchResponseEntry | None:
        return self.adapter.search_by_ura(ura)

    def search_by_agb(self, agb: str) -> ZalSearchResponseEntry | None:
        return self.adapter.search_by_agb(agb)

    def search_by_hrn(self, hrn: str) -> ZalSearchResponseEntry | None:
        return self.adapter.search_by_ura(hrn)

    def search_by_kvk(self, kvk: str) -> ZalSearchResponseEntry | None:
        return self.adapter.search_by_kvk(kvk)
