import pytest

from app.normalization.services import DutchGridTransformerFactory, GeoCoordinateService

DUTCH_GRID_X_COORDINATE = 103341.519
DUTCH_GRID_Y_COORDINATE = 488300.24

EXPECTED_LATITUDE = 52.38013417449228
EXPECTED_LONGITUDE = 4.628503471930447


def test_dutch_grid_to_wgs84_conversion() -> None:
    transformer = DutchGridTransformerFactory.create_transformer()
    service = GeoCoordinateService(transformer)
    result = service.convert_dutch_grid_to_wgs84({"x": DUTCH_GRID_X_COORDINATE, "y": DUTCH_GRID_Y_COORDINATE})
    assert result is not None, "Conversion should return a result"
    latitude, longitude = result
    # Allow a small tolerance for floating point conversion
    assert latitude == EXPECTED_LATITUDE, f"Latitude off: {latitude} vs {EXPECTED_LATITUDE}"
    assert longitude == EXPECTED_LONGITUDE, f"Longitude off: {longitude} vs {EXPECTED_LONGITUDE}"


def test_dutch_grid_to_wgs84_rejects_none() -> None:
    transformer = DutchGridTransformerFactory.create_transformer()
    service = GeoCoordinateService(transformer)
    with pytest.raises(ValueError):
        service.convert_dutch_grid_to_wgs84(None)  # type: ignore[arg-type]
