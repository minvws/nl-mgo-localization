from app.cron.commands.commands import CleanupExpiredImportedOrganisationsCommand
from app.db.repositories import (
    DataServiceRepository,
    DbEndpointRepository,
    IdentifyingFeatureRepository,
    OrganisationRepository,
)
from tests._factories.data_service import create_dataservice
from tests._factories.identifying_feature import create_identifying_feature
from tests._factories.organisation import create_organisation


def test_cleanup_expired_imported_organisations(
    organisation_repository: OrganisationRepository,
    data_service_repository: DataServiceRepository,
    identifying_feature_repository: IdentifyingFeatureRepository,
    endpoint_repository: DbEndpointRepository,
) -> None:
    org_a = create_organisation(organisation_repository, {"import_ref": "1709634749000238"})
    org_b = create_organisation(organisation_repository, {"import_ref": "1709634749000239"})
    org_c = create_organisation(organisation_repository, {"import_ref": "1709634749000240"})

    create_dataservice(data_service_repository, endpoint_repository, {"organisation": org_a})
    create_dataservice(data_service_repository, endpoint_repository, {"organisation": org_b})
    create_dataservice(data_service_repository, endpoint_repository, {"organisation": org_c})

    create_identifying_feature({"organisation": org_a}, identifying_feature_repository)
    create_identifying_feature({"organisation": org_b}, identifying_feature_repository)
    create_identifying_feature({"organisation": org_c}, identifying_feature_repository)

    command = CleanupExpiredImportedOrganisationsCommand()
    status = command.run()

    assert organisation_repository.get_import_refs() == ["1709634749000240", "1709634749000239"]
    assert status == 0
