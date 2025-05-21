from typing import Type

import inject

from .enums import ImportType
from .importers import (
    OrganisationImporter,
    OrganisationJoinListImporter,
    OrganisationListImporter,
)


class OrganisationImporterFactory:
    @staticmethod
    def create_importer(importer_type: ImportType) -> OrganisationImporter:
        type_to_importer: dict[ImportType, Type[OrganisationImporter]] = {
            ImportType.LIST: OrganisationListImporter,
            ImportType.JOIN_LIST: OrganisationJoinListImporter,
        }

        if importer_type not in type_to_importer:
            raise ValueError(f"No importer found for import type '{importer_type}'")

        importer: OrganisationImporter = inject.instance(type_to_importer[importer_type])

        return importer
