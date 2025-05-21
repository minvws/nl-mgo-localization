import pytest
from pytest_mock import MockerFixture

from app.healthcarefinder.healthcarefinder import HealthcareFinder
from app.healthcarefinder.interface import HealthcareFinderAdapter
from app.healthcarefinder.mock.adapter import MockHealthcareFinderAdapter
from app.healthcarefinder.models import SearchRequest, SearchResponse


@pytest.fixture
def mock_healthcarefinder_adapter(mocker: MockerFixture) -> MockHealthcareFinderAdapter:
    return mocker.patch("app.healthcarefinder.mock.adapter.MockHealthcareFinderAdapter")


def test_search_organizations_bypass(
    mocker: MockerFixture,
) -> None:
    mock_healthcarefinder_adapter = mocker.Mock(MockHealthcareFinderAdapter)
    mock_healthcarefinder_adapter.search_organizations.return_value = SearchResponse()
    healthcare_finder_adapter_mock: HealthcareFinderAdapter = mocker.Mock(spec=HealthcareFinderAdapter)
    finder = HealthcareFinder(
        adapter=healthcare_finder_adapter_mock, mock_adapter=mock_healthcarefinder_adapter, allow_search_bypass=True
    )
    search_request = SearchRequest(name="test", city="test")
    response: SearchResponse | None = finder.search_organizations(search=search_request)

    mock_healthcarefinder_adapter.search_organizations.assert_called_once_with(search=search_request)
    assert isinstance(response, SearchResponse)


def test_search_organizations_no_bypass(mocker: MockerFixture) -> None:
    mock_adapter: HealthcareFinderAdapter = mocker.Mock(spec=HealthcareFinderAdapter)

    finder = HealthcareFinder(adapter=mock_adapter, allow_search_bypass=False)
    search_request = SearchRequest(name="not_test", city="not_test")

    # Mock the search_organizations method of HealthcareFinderAdapter
    mock_search_organizations = mocker.patch.object(mock_adapter, "search_organizations", return_value=SearchResponse())

    response: SearchResponse | None = finder.search_organizations(search=search_request)

    mock_search_organizations.assert_called_once_with(search=search_request)
    assert isinstance(response, SearchResponse)


def test_is_search_bypass_requested(mocker: MockerFixture) -> None:
    mock_adapter: HealthcareFinderAdapter = mocker.Mock(spec=HealthcareFinderAdapter)
    finder = HealthcareFinder(adapter=mock_adapter)

    search_request = SearchRequest(name="test", city="test")
    assert finder._HealthcareFinder__is_search_bypass_requested(search=search_request)

    search_request = SearchRequest(name="not_test", city="not_test")
    assert not finder._HealthcareFinder__is_search_bypass_requested(search=search_request)
