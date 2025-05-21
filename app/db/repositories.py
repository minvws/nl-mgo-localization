import json
from typing import Any, Callable, List, TypeVar

from sqlalchemy import ScalarSelect
from sqlalchemy.orm import Session

from app.zal_importer.enums import IdentifyingFeatureType, OrganisationType

from .models import Base, DataService, Endpoint, IdentifyingFeature, Organisation, SystemRole


class BaseRepository:
    def __init__(self, session: Session):
        self._session = session


T = TypeVar("T", bound=type[BaseRepository])

repository_registry: dict[type[Base], type[BaseRepository]] = {}


def repository(model_class: type[Base]) -> Callable[[T], T]:
    def decorator(repo_class: T) -> T:
        """
        Decorator to register a repository for a model class

        :param repo_class:
        :return:
        """
        repository_registry[model_class] = repo_class
        return repo_class

    return decorator


@repository(Organisation)
class OrganisationRepository(BaseRepository):
    def create(
        self,
        name: str,
        type: OrganisationType,
        import_ref: str,
        persist: bool = False,
    ) -> Organisation:
        self._session.add(
            organisation := Organisation(
                name=name,
                type=type,
                import_ref=import_ref,
            )
        )

        if persist:
            self._session.commit()
        else:
            self._session.flush()

        return organisation

    def find_one_by_name(self, name: str) -> Organisation | None:
        return (
            self._session.query(Organisation)
            .filter_by(
                name=name,
                import_ref=self.__latest_import_ref_subquery(),
            )
            .first()
        )

    def find_one_by_identifying_feature(
        self,
        identifying_feature_type: IdentifyingFeatureType,
        identifying_feature_value: str,
    ) -> Organisation | None:
        return (
            self._session.query(Organisation)
            .filter_by(import_ref=self.__latest_import_ref_subquery())
            .join(IdentifyingFeature)
            .filter(
                IdentifyingFeature.type == identifying_feature_type,
                IdentifyingFeature.value == identifying_feature_value,
            )
            .first()
        )

    def has_one_by_import_ref(
        self,
        import_ref: str,
    ) -> bool:
        return self._session.query(Organisation).filter_by(import_ref=import_ref).first() is not None

    def get_import_refs(self) -> List[str]:
        import_refs = (
            self._session.query(Organisation.import_ref).distinct().order_by(Organisation.import_ref.desc()).all()
        )
        return [ref[0] for ref in import_refs]

    def count_by_import_ref(self, import_ref: str) -> int:
        return self._session.query(Organisation).filter_by(import_ref=import_ref).count()

    def delete_by_import_refs(self, import_refs: List[str]) -> None:
        self._session.query(Organisation).filter(Organisation.import_ref.in_(import_refs)).delete(
            synchronize_session=False
        )
        self._session.commit()

    def __latest_import_ref_subquery(self) -> ScalarSelect[Any]:
        return (
            self._session.query(Organisation.import_ref)
            .order_by(Organisation.import_ref.desc())
            .limit(1)
            .scalar_subquery()
        )


@repository(DataService)
class DataServiceRepository(BaseRepository):
    def create(
        self,
        organisation_id: int,
        external_id: str,
        auth_endpoint_id: int,
        token_endpoint_id: int,
        name: str | None = None,
        interface_versions: List[str] | None = None,
        persist: bool = False,
    ) -> DataService:
        interface_versions_json = None
        if interface_versions is not None:
            interface_versions_json = json.dumps(interface_versions)

        self._session.add(
            data_service := DataService(
                name=name,
                organisation_id=organisation_id,
                external_id=external_id,
                interface_versions=interface_versions_json,
                auth_endpoint_id=auth_endpoint_id,
                token_endpoint_id=token_endpoint_id,
            )
        )

        if persist:
            self._session.commit()
        else:
            self._session.flush()

        return data_service

    def find_one_by_organisation_and_external_id(self, organisation_id: int, external_id: str) -> DataService | None:
        return (
            self._session.query(DataService).filter_by(organisation_id=organisation_id, external_id=external_id).first()
        )

    def find_all_by_organisation(self, organisation_id: int) -> List[DataService]:
        return self._session.query(DataService).filter_by(organisation_id=organisation_id).all()


@repository(SystemRole)
class SystemRoleRepository(BaseRepository):
    def create(
        self,
        data_service_id: int,
        code: str,
        resource_endpoint_id: int,
        persist: bool = False,
    ) -> SystemRole:
        self._session.add(
            system_role := SystemRole(
                data_service_id=data_service_id,
                code=code,
                resource_endpoint_id=resource_endpoint_id,
            )
        )

        if persist:
            self._session.commit()
        else:
            self._session.flush()

        return system_role


@repository(IdentifyingFeature)
class IdentifyingFeatureRepository(BaseRepository):
    def create(
        self,
        organisation_id: int,
        type: IdentifyingFeatureType,
        value: str,
        import_ref: str,
        persist: bool = False,
    ) -> IdentifyingFeature:
        self._session.add(
            identifying_feature := IdentifyingFeature(
                organisation_id=organisation_id,
                type=type,
                value=value,
                import_ref=import_ref,
            )
        )

        if persist:
            self._session.commit()
        else:
            self._session.flush()

        return identifying_feature

    def has_one_by_import_ref(self, import_ref: str) -> bool:
        return self._session.query(IdentifyingFeature).filter_by(import_ref=import_ref).first() is not None


@repository(Endpoint)
class EndpointRepository(BaseRepository):
    def create(
        self,
        url: str,
        signature: str | None = None,
        persist: bool = False,
    ) -> Endpoint:
        self._session.add(endpoint := Endpoint(url=url, signature=signature))

        if persist:
            self._session.commit()
        else:
            self._session.flush()

        return endpoint

    def find_one_by_url(self, url: str) -> Endpoint | None:
        return self._session.query(Endpoint).filter_by(url=url).first()

    def find_all(self) -> List[Endpoint]:
        return self._session.query(Endpoint).all()
