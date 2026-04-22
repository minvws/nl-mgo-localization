from __future__ import annotations

from enum import Enum
from typing import List, Self

from pydantic import BaseModel, Field, model_validator

from app.addressing.models import ZalDataServiceResponse


class GeoLocation(BaseModel):
    latitude: float
    longitude: float


class Address(BaseModel):
    active: bool | None = None
    address: str | None = None
    city: str | None
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
    display_name: str | None
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
    name: str | None = None
    city: str | None = None
    text: str | None = None
    medmij_name: str | None = None
    type: str | None = None
    ura: str | None = None
    agb: str | None = None
    kvk: str | None = None

    @model_validator(mode="after")
    def validate_search(self) -> Self:
        if self.text and self.text.strip():
            return self
        if self.medmij_name and self.medmij_name.strip():
            return self
        if self.name and self.name.strip() and self.city and self.city.strip():
            return self
        if self.type and self.type.strip():
            return self
        if self.ura and self.ura.strip():
            return self
        if self.agb and self.agb.strip():
            return self
        if self.kvk and self.kvk.strip():
            return self

        raise ValueError(
            "Either 'text', 'medmij_name', both 'name' and 'city', 'type', 'ura', 'agb', or 'kvk' must be provided"
        )


class TextSearchRequest(BaseModel, str_strip_whitespace=True):
    keys: str = Field(..., description="Free-text search query")


class SearchResponse(BaseModel):
    organizations: List[Organization] = []
