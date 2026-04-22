from __future__ import annotations

import gzip
import logging
import os
import tempfile
from abc import ABC, abstractmethod

from pyproj import Transformer

from app.zal_importer.enums import IdentifyingFeatureType

logger = logging.getLogger(__name__)


class CompressionSizeChecker(ABC):
    @staticmethod
    @abstractmethod
    def get_size_in_kb(file_path: str) -> float | None: ...


class DutchGridTransformerFactory:
    @staticmethod
    def create_transformer() -> Transformer:
        # Convert Dutch national grid (EPSG:28992, "Amersfoort/RD New") to global WGS84 (EPSG:4326) coordinates.
        # Dutch geodata is often provided in the national grid, but most applications use WGS84 (lat/lon).
        return Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)


class GeoCoordinateService:
    def __init__(self, dutch_grid_transformer: Transformer) -> None:
        self._transformer: Transformer = dutch_grid_transformer

    def convert_dutch_grid_to_wgs84(self, dutch_grid_coordinates: dict[str, float]) -> tuple[float, float]:
        if dutch_grid_coordinates is None:
            raise ValueError("dutch_grid_coordinates cannot be None")

        longitude, latitude = self._transformer.transform(dutch_grid_coordinates["x"], dutch_grid_coordinates["y"])

        return latitude, longitude


class GzipCompressionSizeChecker(CompressionSizeChecker):
    @staticmethod
    def get_size_in_kb(file_path: str) -> float | None:
        try:
            with open(file_path, "rb") as source_file, tempfile.NamedTemporaryFile(delete=True) as temp_gzip_file:
                with gzip.GzipFile(fileobj=temp_gzip_file, mode="wb") as gz:
                    gz.write(source_file.read())
                temp_gzip_file.flush()

                return os.path.getsize(temp_gzip_file.name) / 1024
        except Exception:
            return None


class IdStringToIdentifyingFeatureConverter:
    def __call__(self, id_string: str | None) -> tuple[IdentifyingFeatureType, str] | None:
        if id_string is None:
            return None

        if ":" not in id_string:
            logger.warning("Unexpected ID format. Expected 'type:value', got: %s", id_string)
            return None

        id_type, id_value = id_string.split(":", 1)
        try:
            identifying_feature_type = IdentifyingFeatureType(id_type.upper())
        except ValueError:
            logger.warning("Unexpected identifying feature type: %s", id_type)
            return None

        return identifying_feature_type, id_value
