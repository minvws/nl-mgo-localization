import pytest
from pytest_mock import MockerFixture

from app.addressing.models import IdentificationType
from app.zorgab_scraper.config import IdentifierSource
from app.zorgab_scraper.models import Identifier
from app.zorgab_scraper.services import IdentifierProvider, IdentifierRepository


class DummyRepository(IdentifierRepository):
    def __init__(self, identifiers: list[Identifier]) -> None:
        self.identifiers = identifiers
        self.calls = 0
        self.last_limit: int | None | str = "unset"

    def get_identifiers(self, limit: int | None = None) -> list[Identifier]:
        self.calls += 1
        self.last_limit = limit
        return list(self.identifiers)


class TestIdentifierProvider:
    def test_get_identifiers_requires_sources(self) -> None:
        provider = IdentifierProvider(
            repositories={IdentifierSource.zakl_xml: DummyRepository([Identifier(IdentificationType.ura, "1")])},
        )

        with pytest.raises(ValueError, match="At least one identifier source is required"):
            provider.get_identifiers(identifier_sources=[], limit=None)

    def test_get_identifiers_raises_for_unknown_source(self) -> None:
        provider = IdentifierProvider(
            repositories={IdentifierSource.zakl_xml: DummyRepository([Identifier(IdentificationType.ura, "1")])},
        )

        with pytest.raises(ValueError, match="No repository found for source: IdentifierSource.agb_csv"):
            provider.get_identifiers(identifier_sources=[IdentifierSource.agb_csv], limit=None)

    def test_get_identifiers_deduplicates_across_sources(self) -> None:
        repo_a = DummyRepository([Identifier(IdentificationType.ura, "1"), Identifier(IdentificationType.agbz, "2")])
        repo_b = DummyRepository([Identifier(IdentificationType.agbz, "2"), Identifier(IdentificationType.ura, "3")])
        provider = IdentifierProvider(
            repositories={IdentifierSource.zakl_xml: repo_a, IdentifierSource.agb_csv: repo_b},
        )

        combined = provider.get_identifiers(
            identifier_sources=[IdentifierSource.zakl_xml, IdentifierSource.agb_csv], limit=None
        )

        assert set(combined) == {
            Identifier(IdentificationType.ura, "1"),
            Identifier(IdentificationType.agbz, "2"),
            Identifier(IdentificationType.ura, "3"),
        }
        assert repo_a.last_limit is None
        assert repo_b.last_limit is None

    def test_get_identifiers_applies_limit_and_stops_after_first_source(self, mocker: MockerFixture) -> None:
        logger = mocker.patch("app.zorgab_scraper.services.logger")
        repo_a = DummyRepository([Identifier(IdentificationType.ura, "1"), Identifier(IdentificationType.agbz, "2")])
        repo_b = DummyRepository([Identifier(IdentificationType.ura, "3")])
        provider = IdentifierProvider(
            repositories={IdentifierSource.zakl_xml: repo_a, IdentifierSource.agb_csv: repo_b},
        )

        combined = provider.get_identifiers(
            identifier_sources=[IdentifierSource.zakl_xml, IdentifierSource.agb_csv], limit=2
        )

        assert set(combined) == {
            Identifier(IdentificationType.ura, "1"),
            Identifier(IdentificationType.agbz, "2"),
        }
        assert repo_a.calls == 1
        assert repo_b.calls == 0
        logger.info.assert_called_with("Extracted a limited amount of identifiers to first %d (combined)", 2)

    def test_get_identifiers_stops_within_source_when_limit_reached(self, mocker: MockerFixture) -> None:
        repo = DummyRepository(
            [
                Identifier(IdentificationType.ura, "1"),
                Identifier(IdentificationType.agbz, "2"),
                Identifier(IdentificationType.ura, "3"),
            ]
        )
        provider = IdentifierProvider(
            repositories={IdentifierSource.zakl_xml: repo},
        )

        combined = provider.get_identifiers(identifier_sources=[IdentifierSource.zakl_xml], limit=2)

        assert set(combined) == {
            Identifier(IdentificationType.ura, "1"),
            Identifier(IdentificationType.agbz, "2"),
        }
