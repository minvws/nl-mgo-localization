from datetime import date, timedelta
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from app.addressing.models import IdentificationType
from app.zorgab_scraper.config import ZorgABScraperConfig
from app.zorgab_scraper.models import Identifier
from app.zorgab_scraper.services import AgbCsvIdentifierRepository, ZaklXmlIdentifierRepository


def _write_xml(tmp_path: Path, content: str) -> Path:
    xml_path = tmp_path / "zakl.xml"
    xml_path.write_text(content, encoding="utf-8")
    return xml_path


def _write_csv(tmp_path: Path, content: str) -> Path:
    csv_path = tmp_path / "agb.csv"
    csv_path.write_text(content, encoding="utf-8")
    return csv_path


class TestZaklXmlIdentifierRepository:
    def test_get_identifiers_returns_unique_ura_and_agb(self, tmp_path: Path, mocker: MockerFixture) -> None:
        xml_content = """
            <Zorgaanbiederskoppellijst xmlns="xmlns://afsprakenstelsel.medmij.nl/Zorgaanbiederskoppellijst/release1/">
                <Zorgaanbieders>
                    <Zorgaanbieder>
                        <IdentificerendeKenmerken>
                            <IdentificerendKenmerk><URA>123</URA></IdentificerendKenmerk>
                            <IdentificerendKenmerk><AGB>456</AGB></IdentificerendKenmerk>
                        </IdentificerendeKenmerken>
                    </Zorgaanbieder>
                    <Zorgaanbieder>
                        <IdentificerendeKenmerken>
                            <IdentificerendKenmerk><URA>123</URA></IdentificerendKenmerk>
                        </IdentificerendeKenmerken>
                    </Zorgaanbieder>
                </Zorgaanbieders>
            </Zorgaanbiederskoppellijst>
            """
        config = mocker.Mock(spec=ZorgABScraperConfig)
        config.zakl_path = _write_xml(tmp_path, xml_content)

        repository = ZaklXmlIdentifierRepository(config)

        identifiers = repository.get_identifiers()

        assert set(identifiers) == {
            Identifier(IdentificationType.ura, "123"),
            Identifier(IdentificationType.agbz, "456"),
        }

    def test_get_identifiers_applies_limit(self, tmp_path: Path, mocker: MockerFixture) -> None:
        xml_content = """
            <Zorgaanbiederskoppellijst xmlns="xmlns://afsprakenstelsel.medmij.nl/Zorgaanbiederskoppellijst/release1/">
                <Zorgaanbieders>
                    <Zorgaanbieder>
                        <IdentificerendeKenmerken>
                            <IdentificerendKenmerk><URA>123</URA></IdentificerendKenmerk>
                            <IdentificerendKenmerk><AGB>456</AGB></IdentificerendKenmerk>
                        </IdentificerendeKenmerken>
                    </Zorgaanbieder>
                </Zorgaanbieders>
            </Zorgaanbiederskoppellijst>
            """
        config = mocker.Mock(spec=ZorgABScraperConfig)
        config.zakl_path = _write_xml(tmp_path, xml_content)

        repository = ZaklXmlIdentifierRepository(config)

        identifiers = repository.get_identifiers(limit=1)

        assert len(identifiers) == 1

    def test_get_identifiers_skips_missing_values(self, tmp_path: Path, mocker: MockerFixture) -> None:
        xml_content = """
            <Zorgaanbiederskoppellijst xmlns="xmlns://afsprakenstelsel.medmij.nl/Zorgaanbiederskoppellijst/release1/">
                <Zorgaanbieders>
                    <Zorgaanbieder>
                        <IdentificerendeKenmerken>
                        </IdentificerendeKenmerken>
                    </Zorgaanbieder>
                </Zorgaanbieders>
            </Zorgaanbiederskoppellijst>
            """
        config = mocker.Mock(spec=ZorgABScraperConfig)
        config.zakl_path = _write_xml(tmp_path, xml_content)

        repository = ZaklXmlIdentifierRepository(config)

        identifiers = repository.get_identifiers()

        assert identifiers == []

    def test_init_requires_zakl_path(self, mocker: MockerFixture) -> None:
        config = mocker.Mock(spec=ZorgABScraperConfig)
        config.zakl_path = None

        with pytest.raises(
            ValueError, match="When using the ZaklXmlIdentifierRepository, zorgab_scraper.zakl_path must be set"
        ):
            ZaklXmlIdentifierRepository(config)


class TestAgbCsvIdentifierRepository:
    def test_get_identifiers_skips_expired_entries(self, tmp_path: Path, mocker: MockerFixture) -> None:
        csv_content = (
            "KvKnr,AGB_Nummer,AGB_Datumaanvang,AGB_Datumeinde\n1,11111111,20200101,\n2,22222222,20200101,19990101\n"
        )

        config = mocker.Mock(spec=ZorgABScraperConfig)
        config.agb_csv_path = _write_csv(tmp_path, csv_content)

        repository = AgbCsvIdentifierRepository(config)

        identifiers = repository.get_identifiers()

        assert identifiers == [Identifier(IdentificationType.agbz, "11111111")]

    def test_get_identifiers_warns_on_invalid_end_date(self, tmp_path: Path, mocker: MockerFixture) -> None:
        invalid_date = "not-a-date"
        csv_content = (
            "KvKnr,AGB_Nummer,AGB_Datumaanvang,AGB_Datumeinde\n"
            "1,11111111,20200101,\n"
            f"2,22222222,20010101,{invalid_date}\n"
        )

        logger = mocker.patch("app.zorgab_scraper.services.logger")
        config = mocker.Mock(spec=ZorgABScraperConfig)
        config.agb_csv_path = _write_csv(tmp_path, csv_content)

        repository = AgbCsvIdentifierRepository(config)

        identifiers = repository.get_identifiers()

        assert identifiers == [Identifier(IdentificationType.agbz, "11111111")]
        logger.debug.assert_called_once_with("Skipping AGB %s with invalid end date %s", "22222222", invalid_date)

    def test_get_identifiers_includes_future_end_date(self, tmp_path: Path, mocker: MockerFixture) -> None:
        future_date = (date.today() + timedelta(days=10)).strftime("%Y%m%d")
        csv_content = f"KvKnr,AGB_Nummer,AGB_Datumaanvang,AGB_Datumeinde\n1,11111111,20200101,{future_date}\n"

        config = mocker.Mock(spec=ZorgABScraperConfig)
        config.agb_csv_path = _write_csv(tmp_path, csv_content)

        repository = AgbCsvIdentifierRepository(config)

        identifiers = repository.get_identifiers()

        assert identifiers == [Identifier(IdentificationType.agbz, "11111111")]

    def test_get_identifiers_applies_limit_after_deduplication(self, tmp_path: Path, mocker: MockerFixture) -> None:
        csv_content = (
            "KvKnr,AGB_Nummer,AGB_Datumaanvang,AGB_Datumeinde\n"
            "1,11111111,20200101,\n"
            "2,11111111,20200101,\n"
            "3,22222222,20200101,\n"
            "4,33333333,20200101,\n"
        )

        config = mocker.Mock(spec=ZorgABScraperConfig)
        config.agb_csv_path = _write_csv(tmp_path, csv_content)

        repository = AgbCsvIdentifierRepository(config)

        identifiers = repository.get_identifiers(limit=2)

        assert identifiers == [
            Identifier(IdentificationType.agbz, "11111111"),
            Identifier(IdentificationType.agbz, "22222222"),
        ]

    def test_init_requires_agb_csv_path(self, mocker: MockerFixture) -> None:
        config = mocker.Mock(spec=ZorgABScraperConfig)
        config.agb_csv_path = None

        with pytest.raises(
            ValueError, match="When using the AgbCsvIdentifierRepository, zorgab_scraper.agb_csv_path must be set"
        ):
            AgbCsvIdentifierRepository(config)
