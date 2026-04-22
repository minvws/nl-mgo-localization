from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class IdentifierSource(str, Enum):
    zakl_xml = "zakl_xml"
    agb_csv = "agb_csv"


class ZorgABScraperConfig(BaseModel):
    zakl_path: Path | None = Field(default=None)
    agb_csv_path: Path | None = Field(default=None)

    results_base_dir: Path = Field(default=Path("/src/scrape_results"))
