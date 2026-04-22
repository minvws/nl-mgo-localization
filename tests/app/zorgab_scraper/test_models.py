from app.addressing.models import IdentificationType
from app.zorgab_scraper.models import Identifier


def test_identifier_token_returns_type_and_value() -> None:
    identifier = Identifier(IdentificationType.ura, "123")

    assert identifier.token() == "ura:123"
