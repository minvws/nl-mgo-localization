import json
import logging
from abc import ABC, abstractmethod
from csv import DictReader
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree

import inject
from fhir.resources.STU3.bundle import Bundle

from app.addressing.models import IdentificationType

from .config import ZorgABScraperConfig
from .models import Identifier

logger = logging.getLogger(__name__)


class ZorgABJsonFileRepository:
    @inject.autoparams("domain_config")
    def __init__(
        self,
        domain_config: ZorgABScraperConfig,
    ) -> None:
        self.__base_dir: Path = domain_config.results_base_dir
        self.__timestamp_format = "%Y%m%d%H%M%S"

    def write(self, bundle: Bundle) -> str:
        timestamp = datetime.now().strftime(self.__timestamp_format)
        filename: Path = self.__base_dir / f"{timestamp}_zorgab_scrape_results.json"
        filename.parent.mkdir(parents=True, exist_ok=True)

        with filename.open("w", encoding="utf-8") as handle:
            json.dump(bundle.model_dump(mode="json"), handle, ensure_ascii=False, indent=2)

        logger.info("Results saved to %s", filename)

        return str(filename)


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
            reader = DictReader(handle)
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
