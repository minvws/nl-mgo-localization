import argparse
from logging import Logger
from typing import Any, Literal

import inject

from app.addressing.services import EndpointSignatureRenewer
from app.zal_importer.services import ExpiredImportsCleaner

output_template: str = """
[result]
· added: %d
· updated: %d
· skipped: %d
"""


class EndpointSignatureRenewCommand:
    """
    Renew endpoint signatures.
    """

    NAME: str = "endpoint:renew-signatures"

    @staticmethod
    def init_arguments(subparser: Any) -> None:
        subparser.add_parser(EndpointSignatureRenewCommand.NAME, help="Renew all endpoint signatures")

    @inject.autoparams("endpoint_signature_renewer", "logger")
    def run(
        self,
        _: argparse.Namespace,
        endpoint_signature_renewer: EndpointSignatureRenewer,
        logger: Logger,
    ) -> int:
        result = endpoint_signature_renewer.renew()

        logger.info(output_template % (result.added, result.updated, result.skipped))

        return 0


class CleanupExpiredImportedOrganisationsCommand:
    """
    Clean up expired imported organisations.
    """

    NAME: str = "organisation:cleanup-expired"
    __EXPIRED_AFTER_NUM_OF_IMPORTS: int = 2

    @staticmethod
    def init_arguments(subparser: Any) -> None:
        help_text = (
            "Delete expired (older than %d imports ago) imported organisations"
            % CleanupExpiredImportedOrganisationsCommand.__EXPIRED_AFTER_NUM_OF_IMPORTS
        )

        subparser.add_parser(CleanupExpiredImportedOrganisationsCommand.NAME, help=help_text)

    @inject.autoparams()
    def run(self, _: argparse.Namespace, cleaner: ExpiredImportsCleaner) -> Literal[0]:
        cleaner.clean_expired_imports(self.__EXPIRED_AFTER_NUM_OF_IMPORTS)

        return 0
