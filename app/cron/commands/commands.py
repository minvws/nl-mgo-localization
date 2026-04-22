import argparse
from typing import Literal

import inject

from app.cron.utils import SubParsers
from app.zal_importer.services import ExpiredImportsCleaner


class CleanupExpiredImportedOrganisationsCommand:
    """
    Clean up expired imported organisations.
    """

    NAME: str = "organisation:cleanup-expired"
    __EXPIRED_AFTER_NUM_OF_IMPORTS: int = 2

    @staticmethod
    def init_arguments(subparser: SubParsers) -> None:
        help_text = (
            "Delete expired (older than %d imports ago) imported organisations"
            % CleanupExpiredImportedOrganisationsCommand.__EXPIRED_AFTER_NUM_OF_IMPORTS
        )

        subparser.add_parser(CleanupExpiredImportedOrganisationsCommand.NAME, help=help_text)

    @inject.autoparams()
    def run(self, _: argparse.Namespace, cleaner: ExpiredImportsCleaner) -> Literal[0]:
        cleaner.clean_expired_imports(self.__EXPIRED_AFTER_NUM_OF_IMPORTS)

        return 0
