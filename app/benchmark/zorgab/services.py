from __future__ import annotations

from datetime import datetime

import inject

from app.benchmark.zorgab.benchmark import (
    BenchmarkOutputWriter,
    BenchmarkQueryLoader,
    ReciprocalRankScorer,
)
from app.benchmark.zorgab.models import (
    BenchmarkOutput,
    BenchmarkQuery,
    BenchmarkQueryInput,
    BenchmarkQueryResult,
    BenchmarkStats,
)
from app.config.models import Config
from app.healthcarefinder.interface import HealthcareFinderAdapter
from app.healthcarefinder.models import SearchRequest


@inject.autoparams()
class BenchmarkService:
    def __init__(
        self,
        query_loader: BenchmarkQueryLoader,
        rank_scorer: ReciprocalRankScorer,
        output_writer: BenchmarkOutputWriter,
        client: HealthcareFinderAdapter,
        config: Config,
    ) -> None:
        self._query_loader: BenchmarkQueryLoader = query_loader
        self._scorer: ReciprocalRankScorer = rank_scorer
        self._output_writer: BenchmarkOutputWriter = output_writer
        self._zorgab_client: HealthcareFinderAdapter = client
        self._config: Config = config

    def run(
        self,
        *,
        input_data: list[BenchmarkQueryInput] | None,
    ) -> BenchmarkOutput:
        queries: list[BenchmarkQuery] = self._query_loader.load(input_data)
        query_results: list[BenchmarkQueryResult] = []
        stats = BenchmarkStats()

        for query in queries:
            request = SearchRequest(text=query.query)
            response = self._zorgab_client.search_organizations(request)
            organizations = response.organizations if response is not None else []
            mrr, rank_str = self._scorer.score(organizations, query.target_id)
            stats.add(mrr)
            query_results.append(
                BenchmarkQueryResult(
                    query=query.query,
                    target_id=query.target_id,
                    mean_reciprocal_rank=mrr,
                    rank=rank_str,
                )
            )

        output: BenchmarkOutput = {
            "searchProvider": "ZorgAB",
            "searchType": "Full text",
            "executedAt": datetime.now().isoformat(),
            "meanReciprocalRank": stats.mean_total(len(queries)),
            "queries": query_results,
        }

        if self._config.benchmark.zorgab_write_output:
            self._output_writer.write(output)
        return output
