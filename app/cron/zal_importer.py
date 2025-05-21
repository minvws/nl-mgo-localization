import argparse
from typing import Any

import inject
from defusedxml.ElementTree import fromstring

from app.xml.services import ElementTraverser
from app.zal_importer.enums import ImportType
from app.zal_importer.factories import OrganisationImporterFactory


class OrganisationImportCommand:
    """
    Import organisation from MedMij ZAL XML file.
    """

    NAME: str = "organisation:import"

    @staticmethod
    def init_arguments(subparser: Any) -> None:
        parser = subparser.add_parser(OrganisationImportCommand.NAME, help="imports XML files from MedMij")
        parser.add_argument("path", type=str, help="Path to the XML file to import")

    @inject.autoparams()
    def run(self, args: argparse.Namespace, factory: OrganisationImporterFactory) -> int:
        with open(args.path, "r") as f:
            data = f.read()

        xml = fromstring(data)
        traverser = ElementTraverser(xml)

        importer = factory.create_importer(importer_type=ImportType(traverser.get_root_element_name()))
        importer.process_xml(traverser)

        return 0
