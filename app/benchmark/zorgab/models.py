from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from app.benchmark.zorgab.utils import normalize_agb_target_id


class BenchmarkQueryInput(BaseModel):
    query: str
    targetId: str = Field(..., description="Target identifier (e.g. agb:01009626)")


@dataclass(frozen=True, slots=True)
class BenchmarkQuery:
    query: str
    target_id: str


@dataclass(frozen=True, slots=True)
class BenchmarkQueryResult:
    query: str
    target_id: str
    mean_reciprocal_rank: float
    rank: str

    def as_dict(self) -> dict[str, str | float]:
        return {
            "query": self.query,
            "targetId": normalize_agb_target_id(self.target_id),
            "meanReciprocalRank": self.mean_reciprocal_rank,
            "rank": self.rank,
        }


class BenchmarkOutput(TypedDict):
    searchProvider: str
    searchType: str
    executedAt: str
    meanReciprocalRank: float
    queries: list[BenchmarkQueryResult]


@dataclass(slots=True)
class BenchmarkStats:
    mean_reciprocal_rank_total: float = 0.0

    def add(self, mean_reciprocal_rank: float) -> None:
        self.mean_reciprocal_rank_total += mean_reciprocal_rank

    def mean_total(self, n_queries: int) -> float:
        return self.mean_reciprocal_rank_total / n_queries if n_queries else 0.0
