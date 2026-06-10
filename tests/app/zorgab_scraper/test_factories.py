from app.addressing.models import IdentificationType
from app.zorgab_scraper.factories import SearchRequestFactory
from app.zorgab_scraper.models import Identifier


class TestSearchRequestFactory:
    def test_create_for_ura_identifier(self) -> None:
        identifier = Identifier(type=IdentificationType.ura, value="123456789")
        search_request = SearchRequestFactory.create_for_identifier(identifier)

        assert search_request is not None
        assert search_request.ura == "123456789"
        assert search_request.agb is None

    def test_create_for_agbz_identifier(self) -> None:
        identifier = Identifier(type=IdentificationType.agbz, value="987654321")
        search_request = SearchRequestFactory.create_for_identifier(identifier)

        assert search_request is not None
        assert search_request.agb == "987654321"
        assert search_request.ura is None

    def test_create_for_non_agb_or_ura_identifier_returns_none(self) -> None:
        identifier = Identifier(type=IdentificationType.kvk, value="555555555")
        search_request = SearchRequestFactory.create_for_identifier(identifier)

        assert search_request is None
