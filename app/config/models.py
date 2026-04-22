from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.config.utils import lines_to_list
from app.zorgab_scraper.config import ZorgABScraperConfig


class LogLevel(str, Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class HealthcareAdapterType(str, Enum):
    mock_zorgab_hydrated = "mock_zorgab_hydrated"
    mock = "mock"
    zorgab = "zorgab"


class AddressingAdapterType(str, Enum):
    mock = "mock"
    zal = "zal"


class ConfigApp(BaseModel):
    healthcare_adapter: HealthcareAdapterType = Field(default=HealthcareAdapterType.mock)
    addressing_adapter: AddressingAdapterType = Field(default=AddressingAdapterType.mock)
    uvicorn_app: bool = Field(default=False)
    mock_base_url: str
    on_startup_cron_commands: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def parse_on_startup_cron_commands(cls, values: dict[str, Any]) -> dict[str, Any]:  # type: ignore[explicit-any]
        tasks = values.get("on_startup_cron_commands")
        if isinstance(tasks, str):
            values["on_startup_cron_commands"] = lines_to_list(tasks, str)

        return values


class ConfigDatabase(BaseModel):
    dsn: str


class ConfigZorgab(BaseModel):
    base_url: str
    mtls_cert_file: str | None
    mtls_key_file: str | None
    mtls_chain_file: str | None
    proxy: str | None


class ConfigUvicorn(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8006, gt=0, lt=65535)
    reload: bool = Field(default=True)
    use_ssl: bool = Field(default=False)
    ssl_base_dir: str | None
    ssl_cert_file: str | None
    ssl_key_file: str | None


class JWEConfig(BaseModel):
    signing_private_key_path: Path = Field()
    encryption_public_key_path: Path = Field()


class HealthcareFinderConfig(BaseModel):
    allow_search_bypass: bool = Field(default=False)
    suppress_hydration_errors: bool = Field(default=False)


class LoggingConfig(BaseModel):
    logger_name: str = "app"
    log_level: str = "DEBUG"


class BenchmarkConfig(BaseModel):
    zorgab_write_output: bool = Field(default=False)
    zorgab_query_input_path: str = Field(default="resources/benchmark/zorgab/default_input.json")
    zorgab_output_dir: str = Field(default="storage/benchmarks/zorgab/")


class NormalizationConfig(BaseModel):
    """Configuration for normalization outputs."""

    normalization_output_folder: str = Field(default="static/search/normalization")


class SearchIndexationConfig(BaseModel):
    include_mock_organizations: bool = Field(default=False)
    mock_organizations_path: Path = Field(default=Path("resources/search_index/mock-organizations.json"))
    mock_addressing_path: Path = Field(default=Path("resources/search_index/mock-endpoints.json"))


class Config(BaseModel):
    app: ConfigApp

    logging: LoggingConfig = LoggingConfig()
    zorgab: ConfigZorgab
    uvicorn: ConfigUvicorn
    database: ConfigDatabase
    jwe: JWEConfig
    healthcarefinder: HealthcareFinderConfig = HealthcareFinderConfig()
    zorgab_scraper: ZorgABScraperConfig = ZorgABScraperConfig()
    normalization: NormalizationConfig = NormalizationConfig()
    benchmark: BenchmarkConfig = BenchmarkConfig()
    search_indexation: SearchIndexationConfig = SearchIndexationConfig()
