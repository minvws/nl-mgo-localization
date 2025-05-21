from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, RootModel

# Current model information is extracted from https://www.informatieberaadzorg.nl/binaries/informatieberaad-zorg/documenten/publicaties/2020/12/18/zorg-ab-implementatiehandleiding/Bijlage%201a_ZORG-AB%20Implementatiehandleiding%20v2.6.5.pdf


class GeoLocation(BaseModel):
    latitude: float
    longitude: float


class Address(BaseModel):
    active: Optional[bool] = None
    address: str | None = None
    author: str | None = None
    city: str
    country: str | None = None
    firstLine: Optional[str] | None = None
    geolocation: GeoLocation | None = None
    index: str | None = None
    postalCode: str
    state: Optional[str] | None = None
    streetName: str | None = None
    streetNumber: str | None = None
    timestamp: str | None = None
    type: str


class Conformance(BaseModel):
    interactionId: str
    receive: bool
    send: bool


class ElectronicService(BaseModel):
    _className: str
    active: Optional[bool] = False
    address: str | None = None
    applicationId: str | None = None
    author: str
    conformances: List[Conformance] = []
    description: Optional[Any] = None
    index: str
    status: str | None = None
    systemRoles: List[str] = []
    timestamp: str


class Identification(BaseModel):
    active: bool
    author: str
    description: Any
    index: str
    timestamp: str
    type: str
    value: str


class Name(BaseModel):
    active: bool
    author: str
    fullName: str
    index: str
    preferred: bool
    timestamp: str
    type: str


class Telecom(BaseModel):
    active: bool
    author: str
    index: str
    name: str
    preferred: bool
    timestamp: str
    type: str
    value: str


class Type(BaseModel):
    active: Optional[bool] = None
    author: str | None = None
    code: str
    displayName: str
    index: str | None = None
    timestamp: str | None = None
    type: str


class OrganizationModel(BaseModel):
    _self: str
    _className: str
    _id: str
    addresses: List[Address] | None
    applicationIds: List[str] | None
    attachments: Any
    author: str | None
    comment: Any
    credentials: Any
    displayName: str
    electronicServices: List[ElectronicService] | None
    identifications: List[Identification]
    names: List[Name]
    speciality: Any
    telecoms: List[Telecom] | None
    timestamp: str
    type: Any
    types: List[Type]
    ura: Optional[str]


class OrganizationsModel(RootModel[List[OrganizationModel]]):
    root: List[OrganizationModel]
