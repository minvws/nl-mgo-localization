from logging import Logger

import inject

from app.db.repositories import OrganisationRepository


class ExpiredImportsCleaner:
    @inject.autoparams()
    def __init__(self, organisation_repository: OrganisationRepository, logger: Logger) -> None:
        self.__organisation_repository = organisation_repository
        self.__logger = logger

    def clean_expired_imports(self, expiry_threshold: int) -> None:
        import_refs = self.__organisation_repository.get_import_refs()

        self.__logger.info("Found %d import refs: %s", len(import_refs), import_refs)
        import_refs_to_delete = import_refs[expiry_threshold:]
        self.__logger.info("Deleting %d import refs: %s", len(import_refs_to_delete), import_refs_to_delete)

        for import_ref in import_refs_to_delete:
            count = self.__organisation_repository.count_by_import_ref(import_ref)
            self.__logger.info("Found %d organisations to delete for import ref %s", count, import_ref)

        self.__organisation_repository.delete_by_import_refs(import_refs_to_delete)
