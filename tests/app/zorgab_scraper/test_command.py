from argparse import Namespace

import pytest
from pytest_mock import MockerFixture

from app.cron.zorgab_healthcare_scrape_command import ZorgABHealthcareScrapeCommand
from app.zorgab_scraper.config import IdentifierSource


class TestZorgabScrapeCommand:
    def test_init_arguments_adds_parser(self, mocker: MockerFixture) -> None:
        mock_subparser = mocker.MagicMock()
        mock_parser = mocker.MagicMock()
        mock_subparser.add_parser.return_value = mock_parser

        ZorgABHealthcareScrapeCommand.init_arguments(mock_subparser)

        mock_subparser.add_parser.assert_called_once_with(
            "zorgab:scrape",
            help="Scrape ZorgAB for organizations by URA from zakl.xml",
        )
        assert mock_parser.add_argument.call_count == 3

    @pytest.mark.parametrize(
        "limit,workers,identifier_sources",
        [
            (0, 4, [IdentifierSource.zakl_xml]),
            (100, 4, [IdentifierSource.zakl_xml]),
            (0, 12, [IdentifierSource.agb_csv]),
            (-1, 4, [IdentifierSource.zakl_xml, IdentifierSource.agb_csv]),
            (50, 1, [IdentifierSource.zakl_xml]),
        ],
    )
    def test_run_calls_scraper_with_arguments(
        self,
        mocker: MockerFixture,
        limit: int,
        workers: int,
        identifier_sources: list[IdentifierSource],
    ) -> None:
        mock_scraper = mocker.MagicMock()
        command = ZorgABHealthcareScrapeCommand(
            scraper=mock_scraper,
            writer=mocker.MagicMock(),
            logger=mocker.MagicMock(),
        )
        args = Namespace(
            limit=limit,
            workers=workers,
            identifier_sources=identifier_sources,
        )

        exit_code = command.run(args)

        assert exit_code == 0
        mock_scraper.run.assert_called_once_with(
            scrape_limit=limit,
            workers=workers,
            identifier_sources=identifier_sources,
        )
