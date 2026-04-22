from __future__ import annotations

from types import SimpleNamespace

import inject
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.benchmark.zorgab.benchmark import (
    BenchmarkOutputWriter,
    DefaultBenchmarkQueryLoader,
    FileLoader,
    JsonFileOutputWriter,
    ReciprocalRankScorer,
)
from app.benchmark.zorgab.models import BenchmarkOutput, BenchmarkQueryInput
from app.benchmark.zorgab.services import BenchmarkService
from app.healthcarefinder.interface import HealthcareFinderAdapter
from app.healthcarefinder.models import CType, Organization, SearchResponse
from app.healthcarefinder.zorgab.zorgab import ZorgABAdapter
from tests.utils import clear_bindings, configure_bindings


def make_organization(
    *,
    identification: str = "agb:1",
    display_name: str = "Test Organization",
    medmij_id: str | None = None,
    types: list[CType] | None = None,
) -> Organization:
    if types is None:
        types = [CType(code="test", display_name="Test", type="test")]
    return Organization(
        medmij_id=medmij_id,
        display_name=display_name,
        identification=identification,
        types=types,
    )


class TestBenchmarkService:
    def test_run_benchmark_basic(self, test_client: TestClient, mocker: MockerFixture) -> None:
        test_input: list[BenchmarkQueryInput] = [
            BenchmarkQueryInput(query="test", targetId="agb:123"),
            BenchmarkQueryInput(query="test2", targetId="agb:456"),
        ]

        adapter_instance = mocker.Mock(spec=HealthcareFinderAdapter)
        adapter_instance.search_organizations.side_effect = [
            SimpleNamespace(
                organizations=[
                    make_organization(identification="agb:123"),
                    make_organization(identification="agb:999"),
                ]
            ),
            SimpleNamespace(
                organizations=[
                    make_organization(identification="agb:789"),
                    make_organization(identification="agb:456"),
                ]
            ),
        ]

        class _NoopOutputWriter(BenchmarkOutputWriter):
            def write(self, output: BenchmarkOutput) -> None:
                return None

        def bindings_override(binder: inject.Binder) -> inject.Binder:
            binder.bind(FileLoader, FileLoader())
            binder.bind(HealthcareFinderAdapter, adapter_instance)
            binder.bind(BenchmarkOutputWriter, _NoopOutputWriter())
            return binder

        configure_bindings(bindings_override)
        benchmark_service: BenchmarkService = inject.instance(BenchmarkService)
        result = benchmark_service.run(input_data=test_input)

        assert result["searchProvider"] == "ZorgAB"
        assert result["searchType"] == "Full text"
        assert result["meanReciprocalRank"] > 0
        assert result["queries"][0].mean_reciprocal_rank == 1.0
        assert result["queries"][1].mean_reciprocal_rank == 0.5
        assert result["queries"][0].rank == "1/2"
        assert result["queries"][1].rank == "2/2"


class TestReciprocalRankScorer:
    def test_scorer_handles_agb_formats(self) -> None:
        scorer = ReciprocalRankScorer()
        organizations = [make_organization(identification="agb:0101")]

        result = scorer.score(organizations=organizations, target_id="agb:0101")
        assert result == (1.0, "1/1")

    def test_scorer_normalizes_agb_z_identification(self) -> None:
        scorer = ReciprocalRankScorer()
        organizations = [make_organization(identification="agb-z:0101")]

        result = scorer.score(organizations=organizations, target_id="agb:0101")

        assert result == (1.0, "1/1")

    def test_scorer_handles_missing_identification(self) -> None:
        scorer = ReciprocalRankScorer()
        organizations = [make_organization(identification="")]

        result = scorer.score(organizations, "agb:0101")

        assert result == (0.0, "NOT FOUND")


class FakeFileLoader:
    def __init__(self, data: list[BenchmarkQueryInput]):
        self.data = data

    def load(self, path: str) -> list[BenchmarkQueryInput]:  # pragma: no cover - trivial
        return self.data


def test_default_loader_allows_missing_type_field() -> None:
    input_data = [BenchmarkQueryInput(query="Q", targetId="agb:1")]

    def bindings_override(binder: inject.Binder) -> inject.Binder:
        binder.bind(FileLoader, FakeFileLoader(input_data))

        return binder

    configure_bindings(bindings_override)

    try:
        loader = inject.instance(DefaultBenchmarkQueryLoader)
        queries = loader.load(None)
    finally:
        clear_bindings()
    assert len(queries) == 1
    assert queries[0].query == "Q"
    assert queries[0].target_id == "agb:1"


def test_benchmark_zorgab_endpoint_serializes_results(
    test_client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        ZorgABAdapter,
        "search_organizations",
        return_value=SearchResponse(organizations=[make_organization(identification="agb:123")]),
    )
    mocker.patch.object(JsonFileOutputWriter, "write", return_value=None)

    response = test_client.post(
        "/benchmark/zorgab",
        json=[{"query": "test", "targetId": "agb:123"}],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["queries"][0]["query"] == "test"
    assert payload["queries"][0]["targetId"] == "agb:123"
    assert payload["queries"][0]["rank"] == "1/1"
    assert payload["queries"][0]["meanReciprocalRank"] == 1.0
