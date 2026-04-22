import csv
import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from threading import Lock
from xml.etree import ElementTree

import inject
from fhir.resources.STU3.bundle import Bundle

from app.addressing.models import IdentificationType
from app.healthcarefinder.interface import HealthcareFinderAdapter
from app.zorgab_scraper.config import IdentifierSource, ZorgABScraperConfig
from app.zorgab_scraper.factories import SearchRequestFactory
from app.zorgab_scraper.models import Identifier, ScrapeResult

logger = logging.getLogger(__name__)


class IdentifierRepository(ABC):
    @abstractmethod
    def get_identifiers(self, limit: int | None = None) -> list[Identifier]: ...


class ZaklXmlIdentifierRepository(IdentifierRepository):
    @inject.autoparams("zorgab_scrape_config")
    def __init__(self, zorgab_scrape_config: ZorgABScraperConfig) -> None:
        if not zorgab_scrape_config.zakl_path:
            raise ValueError("When using the ZaklXmlIdentifierRepository, zorgab_scraper.zakl_path must be set")
        self.__path = zorgab_scrape_config.zakl_path

    def get_identifiers(self, limit: int | None = None) -> list[Identifier]:
        tree = ElementTree.parse(self.__path)
        root = tree.getroot()
        ns = {"zakl": "xmlns://afsprakenstelsel.medmij.nl/Zorgaanbiederskoppellijst/release1/"}

        identifiers: set[Identifier] = set()

        for zorgaanbieder in root.findall(".//zakl:Zorgaanbieder", ns):
            ura_elem = zorgaanbieder.find(".//zakl:URA", ns)
            if ura_elem is not None and ura_elem.text:
                identifiers.add(Identifier(IdentificationType.ura, ura_elem.text.strip()))

            agb_elem = zorgaanbieder.find(".//zakl:AGB", ns)
            if agb_elem is not None and agb_elem.text:
                identifiers.add(Identifier(IdentificationType.agbz, agb_elem.text.strip()))

        identifier_list = list(identifiers)
        total_found = len(identifier_list)

        if limit is not None and limit > 0:
            identifier_list = identifier_list[:limit]
            logger.info(
                "Extracted a limited amount of identifiers to first %d of %d",
                len(identifier_list),
                total_found,
            )
        else:
            logger.info("Extracted %d identifiers from %s", total_found, self.__path.name)

        return identifier_list


class AgbCsvIdentifierRepository(IdentifierRepository):
    @inject.autoparams("zorgab_scrape_config")
    def __init__(self, zorgab_scrape_config: ZorgABScraperConfig) -> None:
        if not zorgab_scrape_config.agb_csv_path:
            raise ValueError("When using the AgbCsvIdentifierRepository, zorgab_scraper.agb_csv_path must be set")

        self.__path = zorgab_scrape_config.agb_csv_path

    def get_identifiers(self, limit: int | None = None) -> list[Identifier]:
        today = date.today()
        identifiers: list[Identifier] = []
        seen: set[str] = set()

        with self.__path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                agb_value = (row.get("AGB_Nummer") or "").strip()
                if not agb_value or agb_value in seen:
                    continue

                end_date_raw = (row.get("AGB_Datumeinde") or "").strip()
                if end_date_raw:
                    try:
                        end_date = datetime.strptime(end_date_raw, "%Y%m%d").date()
                    except ValueError:
                        logger.debug("Skipping AGB %s with invalid end date %s", agb_value, end_date_raw)
                        continue

                    if end_date < today:
                        continue

                seen.add(agb_value)
                identifiers.append(Identifier(IdentificationType.agbz, agb_value))

        total_found = len(identifiers)

        if limit is not None and limit > 0 and total_found > limit:
            identifiers = identifiers[:limit]
            logger.info(
                "Extracted a limited amount of identifiers to first %d of %d",
                len(identifiers),
                total_found,
            )
        else:
            logger.info("Extracted %d identifiers from %s", total_found, self.__path.name)

        return identifiers


class IdentifierProvider:
    @inject.autoparams("repositories")
    def __init__(self, repositories: dict[IdentifierSource, IdentifierRepository]) -> None:
        self.__repositories: dict[IdentifierSource, IdentifierRepository] = repositories

    def get_identifiers(self, identifier_sources: list[IdentifierSource], limit: int | None = None) -> list[Identifier]:
        """Collect identifiers from configured sources and deduplicate request tokens.

        This is the first deduplication layer: it removes duplicate `type:value` identifiers
        before scraping so we do not perform the same lookup multiple times.

        A second deduplication layer exists later in bundle merging, because different
        identifier lookups (for example AGB and URA) can still return the same organization.
        """
        if not identifier_sources:
            raise ValueError("At least one identifier source is required")

        seen: set[Identifier] = set()  # set enforces deduplication
        seen_count: int = 0
        max_items = limit if limit and limit > 0 else None

        logger.info("Started to extract identifiers from sources...")

        for identifier_source in identifier_sources:
            repository = self.__repositories.get(identifier_source)

            if repository is None:
                raise ValueError(f"No repository found for source: {identifier_source}")

            identifiers = repository.get_identifiers(limit=None)

            for identifier in identifiers:
                if identifier in seen:
                    logger.debug(
                        "Identifier already seen and skipped: %s:%s",
                        identifier.type,
                        identifier.value,
                    )
                    continue

                if max_items is not None and seen_count >= max_items:
                    break

                seen.add(identifier)
                seen_count += 1

            if max_items is not None and seen_count >= max_items:
                break

        if max_items is not None and seen_count >= max_items:
            logger.info("Extracted a limited amount of identifiers to first %d (combined)", max_items)
        else:
            logger.info("Extracted a total of %d identifiers from %d sources", seen_count, len(identifier_sources))

        return list(seen)


class ZorgabScrapeExecutor:
    @inject.autoparams("healthcare_finder")
    def __init__(self, healthcare_finder: HealthcareFinderAdapter) -> None:
        self.__healthcare_finder = healthcare_finder

    def __filter_valid_identifiers(self, identifiers: Sequence[Identifier]) -> list[Identifier]:
        return [
            identifier
            for identifier in identifiers
            if SearchRequestFactory.create_for_identifier(identifier) is not None
        ]

    def execute(self, identifiers: Sequence[Identifier], workers: int) -> ScrapeResult:
        """
        Method responsible for executing the entire scrape process.
        It validates identifiers it received to ensure only supported types are used (agb and ura).
        Then it performs concurrent searches for organizations using the HealthcareFinderAdapter.
        Finally, it collects the results into a ScrapeResult object.
        This ScrapeResult contains found bundles, so a bundle for each successful search.

        """
        if not identifiers:
            raise ValueError("No identifiers to scrape")

        valid_identifiers = self.__filter_valid_identifiers(identifiers)

        if not valid_identifiers:
            raise ValueError("No supported identifiers to scrape")

        max_workers = max(1, min(workers, len(valid_identifiers)))

        logger.info(
            "Started scraping zorgab for %d identifiers using %d workers. This may take a while...",
            len(identifiers),
            workers,
        )

        bundles: list[Bundle] = []
        not_found: list[str] = []
        errors: list[str] = []
        lock = Lock()

        # Define the function that performs the find request so it can be used in threads
        def perform_find_request(identifier: Identifier) -> None:
            search = SearchRequestFactory.create_for_identifier(identifier)
            assert search is not None

            try:
                raw_fhir = self.__healthcare_finder.search_organizations_raw_fhir(search)
                if raw_fhir and raw_fhir.entry:
                    result_count = len(raw_fhir.entry)
                    if result_count > 1:
                        logger.debug(
                            "Multiple organizations returned for %s: %d",
                            identifier.token().upper(),
                            result_count,
                        )

                    with lock:
                        bundles.append(raw_fhir)
                    return

                logger.debug("No organizations found for %s", identifier.token().upper())
                with lock:
                    not_found.append(identifier.token().upper())
                return
            except Exception as exc:
                logger.exception("Error searching for %s", identifier.token().upper())
                with lock:
                    errors.append(f"{identifier.token().upper()}: {exc}")
                return

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(perform_find_request, identifier) for identifier in valid_identifiers]
            for future in as_completed(futures):
                future.result()

        return ScrapeResult(bundles=bundles, not_found=not_found, errors=errors)
