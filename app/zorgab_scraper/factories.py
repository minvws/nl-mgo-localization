from app.addressing.models import IdentificationType
from app.healthcarefinder.models import SearchRequest
from app.zorgab_scraper.models import Identifier


class SearchRequestFactory:
    @staticmethod
    def create_for_identifier(identifier: Identifier) -> SearchRequest | None:
        """Create a search request for the given identifier."""
        if identifier.type == IdentificationType.ura:
            return SearchRequest(ura=identifier.value)
        if identifier.type == IdentificationType.agbz:
            return SearchRequest(agb=identifier.value)
        return None
