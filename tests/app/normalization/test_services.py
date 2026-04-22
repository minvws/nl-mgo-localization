import os
import tempfile

from faker import Faker
from pytest_mock import MockerFixture

from app.normalization.services import GzipCompressionSizeChecker, IdStringToIdentifyingFeatureConverter
from app.zal_importer.enums import IdentifyingFeatureType


class TestGzipCompressionSizeChecker:
    def test_get_size_in_kb_success(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            f.write('{"test": "data", "number": 123}')
            temp_file = f.name

        try:
            size_kb = GzipCompressionSizeChecker.get_size_in_kb(temp_file)
            assert size_kb is not None
            assert isinstance(size_kb, float)
            assert size_kb > 0
            assert size_kb < 1
        finally:
            os.unlink(temp_file)

    def test_get_size_in_kb_file_not_found(self) -> None:
        size_kb = GzipCompressionSizeChecker.get_size_in_kb("/nonexistent/file.json")
        assert size_kb is None

    def test_get_size_in_kb_gzip_error(self, mocker: MockerFixture) -> None:
        mocker.patch("gzip.GzipFile", side_effect=Exception("Gzip error"))

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            f.write('{"test": "data"}')
            temp_file = f.name

        try:
            size_kb = GzipCompressionSizeChecker.get_size_in_kb(temp_file)
            assert size_kb is None
        finally:
            os.unlink(temp_file)


class TestIdStringToIdentifyingFeatureConverter:
    def test_call_when_id_string_valid_returns_tuple(self, faker: Faker) -> None:
        id_type = faker.random_element(IdentifyingFeatureType)
        id_value = faker.numerify("######")
        sut = IdStringToIdentifyingFeatureConverter()

        result = sut(f"{id_type.value}:{id_value}")

        assert result == (id_type, id_value)

    def test_call_when_id_string_none_returns_none(self) -> None:
        sut = IdStringToIdentifyingFeatureConverter()

        result = sut(None)

        assert result is None

    def test_call_when_id_string_invalid_format_returns_none(self, mocker: MockerFixture) -> None:
        mock_logger = mocker.patch("app.normalization.services.logger")
        invalid_id_string = "invalid_id_string"
        sut = IdStringToIdentifyingFeatureConverter()

        result = sut(invalid_id_string)

        assert result is None

        mock_logger.warning.assert_called_once_with(
            "Unexpected ID format. Expected 'type:value', got: %s", invalid_id_string
        )

    def test_call_when_id_string_has_unknown_type_returns_none(self, mocker: MockerFixture, faker: Faker) -> None:
        mock_logger = mocker.patch("app.normalization.services.logger")
        unknown_id_type = "unknown_type"
        id_value = faker.numerify("######")
        sut = IdStringToIdentifyingFeatureConverter()

        result = sut(f"{unknown_id_type}:{id_value}")

        assert result is None

        mock_logger.warning.assert_called_once_with("Unexpected identifying feature type: %s", unknown_id_type)
