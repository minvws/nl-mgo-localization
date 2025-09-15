from __future__ import annotations

from enum import Enum
from typing import List, Self

from pydantic import BaseModel, model_validator

from app.addressing.models import ZalDataServiceResponse


class GeoLocation(BaseModel):
    latitude: float
    longitude: float


class Address(BaseModel):
    active: bool | None = None
    address: str | None = None
    city: str
    country: str | None
    lines: List[str] | None = None
    geolocation: GeoLocation | None = None
    postalcode: str | None = None
    state: str | None = None


class Name(BaseModel):
    full_name: str
    preferred: bool


class CType(BaseModel):
    code: str
    display_name: str
    type: str


class Identification(BaseModel):
    identification_type: str | None
    identification_value: str | None

    @model_validator(mode="after")
    def validate_identifier(self) -> Self:
        if self.identification_type is None and self.identification_value is None:
            raise ValueError("At least one of identification_type or identification_value must be provided")

        return self

    def __str__(self) -> str:
        return f"{self.identification_type}:{self.identification_value}"


class Organization(BaseModel):
    medmij_id: str | None
    display_name: str
    identification: str
    addresses: List[Address] = []
    types: List[CType]
    data_services: List[ZalDataServiceResponse] = []


class SearchType(Enum):
    NONE = ""
    DOCTOR = "doctor"
    HOSPITAL = "hospital"
    DENTIST = "dentist"


class SearchRequest(BaseModel, str_strip_whitespace=True):
    name: str
    city: str


class SearchResponse(BaseModel):
    organizations: List[Organization] = []
