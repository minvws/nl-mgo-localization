from enum import Enum
from typing import Optional, Self

from pydantic import BaseModel, Field, model_validator


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
    mock_base_url: str | None = None

    @model_validator(mode="after")
    def assert_mock_base_url_is_required_when_healthcare_adapter_mock(self) -> Self:
        if self.healthcare_adapter != HealthcareAdapterType.mock:
            return self

        if self.mock_base_url is None:
            raise ValueError('"mock_base_url" is required when using the mock addressing adapter')

        return self


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


class SigningConfig(BaseModel):
    sign_endpoints: bool = Field(default=True)
    private_key_path: Optional[str] = None

    @model_validator(mode="after")
    def assert_required_fields_when_signing_is_enabled(self) -> Self:
        if not self.sign_endpoints:
            return self

        if self.private_key_path is None:
            raise ValueError('"private_key_path" is required when signing is enabled')

        return self


class HealthcareFinderConfig(BaseModel):
    allow_search_bypass: bool = Field(default=False)


class LoggingConfig(BaseModel):
    logger_name: str = "app"
    log_level: str = "DEBUG"


class Config(BaseModel):
    app: ConfigApp
    logging: LoggingConfig = LoggingConfig()
    zorgab: ConfigZorgab
    uvicorn: ConfigUvicorn
    database: ConfigDatabase
    signing: SigningConfig
    healthcarefinder: HealthcareFinderConfig = HealthcareFinderConfig()
