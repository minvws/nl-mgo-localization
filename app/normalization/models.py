from typing_extensions import TypedDict


class NormalizedDataService(TypedDict):
    id: str
    auth_endpoint: str
    token_endpoint: str
    resource_endpoint: str


class NormalizedOrganization(TypedDict, total=False):
    id: str
    medmij_id: str
    name: str
    aliases: list[str]
    care_type: str
    city: str
    postal_code: str
    address: str | None
    geo_lat: float | None
    geo_lng: float | None
    search_blob: str
    data_services: list[NormalizedDataService]
