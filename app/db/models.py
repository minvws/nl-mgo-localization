from __future__ import annotations

from typing import List

from pydantic import BaseModel
from sqlalchemy import JSON, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.zal_importer.enums import IdentifyingFeatureType, OrganisationType


class Base(DeclarativeBase):
    pass


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    name: Mapped[str] = mapped_column("name", String(100), nullable=False)

    def __repr__(self) -> str:
        return f"<City(id={self.id}, name={self.name})>"


class Meta(BaseModel):
    limit: int
    offset: int
    total: int


class CityResponse(BaseModel):
    meta: Meta
    items: List[str]


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    name: Mapped[str] = mapped_column("name", String(255), nullable=False)
    type: Mapped[OrganisationType] = mapped_column("type", Enum(OrganisationType), nullable=False)
    import_ref: Mapped[str] = mapped_column("import_ref", String(24), nullable=False)

    def __repr__(self) -> str:
        return f"<Organisation(id={self.id}, name={self.name}, type={self.type}, import_ref={self.import_ref})>"


class IdentifyingFeature(Base):
    __tablename__ = "identifying_features"

    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"))
    type: Mapped[IdentifyingFeatureType] = mapped_column("type", Enum(IdentifyingFeatureType), nullable=False)
    value: Mapped[str] = mapped_column("value", String(32), nullable=False)
    import_ref: Mapped[str] = mapped_column("import_ref", String(24), nullable=False)

    def __repr__(self) -> str:
        return f"""
        <IdentifyingFeature(
            id={self.id},
            type={self.type},
            value={self.value},
            organisation_id={self.organisation_id}
        )>
        """


class DataService(Base):
    __tablename__ = "data_services"

    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"))
    external_id: Mapped[str] = mapped_column("external_id", String(32), nullable=False)
    name: Mapped[str] = mapped_column("name", String(255), nullable=True)
    interface_versions: Mapped[str] = mapped_column("interface_versions", JSON, nullable=True)
    auth_endpoint_id: Mapped[int] = mapped_column(ForeignKey("endpoints.id", ondelete="SET NULL"))
    token_endpoint_id: Mapped[int] = mapped_column(ForeignKey("endpoints.id", ondelete="SET NULL"))

    roles: Mapped[List[SystemRole]] = relationship("SystemRole", back_populates="data_service")
    auth_endpoint: Mapped[Endpoint] = relationship("Endpoint", foreign_keys=[auth_endpoint_id])
    token_endpoint: Mapped[Endpoint] = relationship("Endpoint", foreign_keys=[token_endpoint_id])

    def __repr__(self) -> str:
        return f"""
        <DataService(
            id={self.id},
            name={self.name},
            interface_versions={self.interface_versions},
            auth_endpoint={self.auth_endpoint},
            token_endpoint={self.token_endpoint},
            organisation_id={self.organisation_id}
        )>
        """


class SystemRole(Base):
    __tablename__ = "system_roles"

    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    data_service_id: Mapped[int] = mapped_column(ForeignKey("data_services.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column("code", String(32), nullable=False)
    resource_endpoint_id: Mapped[int] = mapped_column(ForeignKey("endpoints.id", ondelete="SET NULL"))

    data_service: Mapped[DataService] = relationship("DataService", back_populates="roles")
    resource_endpoint: Mapped[Endpoint] = relationship("Endpoint", foreign_keys=[resource_endpoint_id])

    def __repr__(self) -> str:
        return f"""
        <SystemRole(
            id={self.id},
            code={self.code},
            resource_endpoint={self.resource_endpoint},
            data_service_id={self.data_service_id}
        )>
        """


class Endpoint(Base):
    __tablename__ = "endpoints"

    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    url: Mapped[str] = mapped_column("url", Text, nullable=False)
    signature: Mapped[str | None] = mapped_column("signature", String(100), nullable=True)

    def __repr__(self) -> str:
        return f"""
        <Endpoint(
            id={self.id},
            url={self.url},
            signature={self.signature},
        )>
        """
