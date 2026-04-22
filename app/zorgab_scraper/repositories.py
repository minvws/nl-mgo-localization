import json
from datetime import datetime
from logging import Logger
from pathlib import Path

import inject
from fhir.resources.STU3.bundle import Bundle

from app.zorgab_scraper.config import ZorgABScraperConfig


class ZorgABJsonFileRepository:
    @inject.autoparams("logger", "domain_config")
    def __init__(
        self,
        logger: Logger,
        domain_config: ZorgABScraperConfig,
    ) -> None:
        self.__base_dir: Path = domain_config.results_base_dir
        self.__logger = logger
        self.__timestamp_format = "%Y%m%d%H%M%S"

    def write(self, bundle: Bundle) -> str:
        timestamp = datetime.now().strftime(self.__timestamp_format)
        filename: Path = self.__base_dir / f"{timestamp}_zorgab_scrape_results.json"
        filename.parent.mkdir(parents=True, exist_ok=True)

        with filename.open("w", encoding="utf-8") as handle:
            json.dump(bundle.model_dump(mode="json"), handle, ensure_ascii=False, indent=2)

        self.__logger.info("Results saved to %s", filename)
        return str(filename)
