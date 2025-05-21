from enum import Enum
from typing import List

from pydantic import BaseModel


class ZalDataServiceRoleResponse(BaseModel):
    code: str
    resource_endpoint: str


class ZalDataServiceResponse(BaseModel):
    id: str
    name: str
    interface_versions: List[str]
    auth_endpoint: str
    token_endpoint: str
    roles: List[ZalDataServiceRoleResponse]


class ZalSearchResponseEntry(BaseModel):
    medmij_id: str
    organization_type: str
    id_type: str
    id_value: str
    dataservices: List[ZalDataServiceResponse]


class IdentificationType(str, Enum):
    agbz = "agb-z"
    medmij = "medmij"
    hrn = "htn"
    ura = "ura"
    kvk = "kvk"


class ZalSearchRequestEntry(BaseModel):
    id_type: IdentificationType
    id_value: str
