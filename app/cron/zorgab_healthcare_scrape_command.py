import argparse
from logging import Logger

import inject

from app.cron.arg_types import ListType
from app.cron.utils import SubParsers
from app.zorgab_scraper.config import IdentifierSource
from app.zorgab_scraper.repositories import ZorgABJsonFileRepository
from app.zorgab_scraper.scraper import ZorgabScraper


class ZorgABHealthcareScrapeCommand:
    NAME: str = "zorgab:scrape"

    @inject.autoparams("scraper", "writer", "logger")
    def __init__(self, scraper: ZorgabScraper, writer: ZorgABJsonFileRepository, logger: Logger) -> None:
        self.__scraper = scraper
        self.__writer = writer
        self.__logger = logger

    @staticmethod
    def init_arguments(subparser: SubParsers) -> None:
        parser = subparser.add_parser(
            ZorgABHealthcareScrapeCommand.NAME,
            help="Scrape ZorgAB for organizations by URA from zakl.xml",
        )
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=0,
            help="Maximum number of identifiers to process; set to 0 or negative for no limit",
        )
        parser.add_argument(
            "--workers",
            "-w",
            type=int,
            default=4,
            help="Number of concurrent workers to use; set to 1 to disable concurrency",
        )
        parser.add_argument(
            "--identifier-sources",
            "-s",
            type=ListType(IdentifierSource),
            default=list(IdentifierSource),
            help="Comma-separated list of identifier sources",
        )

    def run(self, args: argparse.Namespace) -> int:
        bundle = self.__scraper.run(
            scrape_limit=args.limit,
            workers=args.workers,
            identifier_sources=args.identifier_sources,
        )
        filename = self.__writer.write(bundle)
        self.__logger.info("Zorgab scrape saved to %s", filename)

        return 0
